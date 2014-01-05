#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# $Id$

import os, sys, re
import time, math
import wave
import subprocess
import multiprocessing


class Decode:
	""" Decoder """
	def __init__(self, filename):
		self.filename = filename
		self.origin_filename = None

		self.fileext = {
			'.tta' 	: self.tta,
			'.flac' : self.flac,
			'.ape' 	: self.ape,
			'.wv'	: self.wv,
		}

		if not os.path.exists(filename):
			# try to find an encoded file and decode it to wave format
			for extension, dec_func in self.fileext.iteritems():
				filename = os.path.splitext(filename)[0] + extension
				if os.path.exists(filename):
					print 'Decode:', filename
					self.origin_filename = filename
					dec_func()
					break

	def __del__(self):
		if self.origin_filename:
			os.remove(self.filename)

	def ape(self):
		subprocess.call(['mac',
			self.origin_filename,
			self.filename,
			'-d',
		] )

	def flac(self):
		subprocess.call(['flac',
			'-d',
			self.origin_filename,
		] )

	def tta(self):
		subprocess.call(['ttaenc',
			'-d',
			self.origin_filename,
			'.',
		] )

	def wv(self):
		subprocess.call(['wvunpack',
			self.origin_filename,
			'.',
		] )


class Track:
	def __init__(self, track_index, file, parent):

		# from parent
		for member in ('cd_performer', 'cd_title', 'cd_date', 'cd_genre'):
			setattr(self, member, getattr(parent, member))

		self.file = file
		self.title = ''
		self.index = track_index
		self.performer = self.cd_performer
		self.time = { 1:0.0 }

	def __str__(self):
		return "{} - {} - {}".format(self.index, self.title, self.time)



class CueSheet:

	def __init__(self, cue_sheet):
		self.sheet = cue_sheet
		self.cd_performer = ''
		self.cd_title = ''
		self.cd_genre = ''
		self.cd_date = ''

		self.current_file = ''

		self.tracks = []

		self.regex_lst = (
			(re.compile(r'PERFORMER\s(.+)'), self.__performer),
			(re.compile(r'REM DATE\s(.+)'), self.__date),
			(re.compile(r'REM GENRE\s(.+)'), self.__genre),
			(re.compile(r'TITLE\s(.+)'), self.__title),
			(re.compile(r'FILE\s(.+)\sWAVE'), self.__file), # only wave
			(re.compile(r'TRACK\s(\d{2})\sAUDIO'), self.__track), # only audio
			(re.compile(r'INDEX\s(\d{2})\s(\d{1,3}:\d{2}:\d{2})'), self.__index),
		)


	def __performer(self, s):
		if not self.tracks:
			self.cd_performer = s
		else:
			self.tracks[-1].performer = s

	def __title(self, s):
		if not self.tracks:
			self.cd_title = s
		else:
			self.tracks[-1].title = s

	def __genre(self, s):
		self.cd_genre = s

	def __date(self, s):
		self.cd_date = s

	def __file(self, s):
		self.current_file = s

	def __track(self, s):
		self.tracks.append( Track(s, self.current_file, self) )

	@staticmethod
	def index_split(s):
		t = s.split(':')
		return (int(t[0])*60 + int(t[1]))*75 + int(t[2])
	@staticmethod
	def dqstrip(s):
		if s[0] == '"' and s[-1] == '"': return s[1:-1]
		return s

	@staticmethod
	def unquote(t):
		return tuple([CueSheet.dqstrip(s.strip()) for s in t])

	def __index(self, idx, s):
		idx = int(idx)
		self.tracks[-1].time[idx] = self.index_split(s)


	def read(self):
		for line in open(self.sheet):
			for regex, handler in self.regex_lst:
				mobj = regex.match(line.strip())
				if mobj:
					#~ print mobj.group(1)
					handler(*self.unquote(mobj.groups()))

		#~ for x in self.tracks: print x


	def split(self, encoders=None):
		encoding_queue = multiprocessing.Queue(multiprocessing.cpu_count())

		keep_alive = []	# a dummy object
		for i, track in enumerate(self.tracks):
			keep_alive.append( Decode(track.file) )

			wafi = wave.open(track.file, 'rb')
			param_names = ('nchannels', 'sampwidth', 'framerate', 'nframes', 'comptype', 'compname')
			params = wafi.getparams()
			param_dict = dict(zip(param_names, params))

			#~ print param_dict['framerate']

			# calculate number of frames
			start = param_dict['framerate'] * track.time[1] // 75
			stop = param_dict['nframes']
			if len(self.tracks) > i+1 and self.tracks[i+1].file == track.file:
				stop = int(param_dict['framerate'] * self.tracks[i+1].time.get(0, self.tracks[i+1].time[1])) // 75


			trackfilename = ' - '.join((track.index, track.title)) + '.wav'
			trackfilename = trackfilename.replace('?', '')
			trackfilename = trackfilename.replace('/', '')
			trackfilename = trackfilename.replace('\\', '')
			trackfilename = trackfilename.replace(':', '')

			if not os.path.exists(trackfilename):
				wafi_write = wave.open(trackfilename, 'wb')
				newparams = list(params)
				newparams[3] = 0
				wafi_write.setparams( tuple(newparams) )

				wafi.setpos(start)
				wafi_write.writeframes(wafi.readframes(stop-start))
				wafi_write.close()

			wafi.close()


			# ogg encode it, queue is used for sync
			for encode_to in encoders:
				encoding_queue.put(trackfilename)
				p = multiprocessing.Process(target=encode_to, args=(
					encoding_queue,
					trackfilename,
					track
					))
				p.start()

		# wait until all task are finished
		while not encoding_queue.empty():
			time.sleep(1.0)

		keep_alive = None


	def __str__(self):
		output = 'REM COMMENT CUE JOIN\n'
		if self.cd_genre: output += 'REM GENRE "{}"\n'.format(self.cd_genre)
		if self.cd_date: output += 'REM DATE {}\n'.format(self.cd_date)
		if self.cd_performer: output += 'PERFORMER "{}"\n'.format(self.cd_performer)
		if self.cd_title: output += 'TITLE "{}"\n'.format(self.cd_title)
		one_file = self.tracks[0].file == self.tracks[-1].file
		if one_file: output += u'FILE "{}" WAVE\n'.format(self.current_file).encode('latin-1')
		for i, track in enumerate(self.tracks):
			output += '  TRACK {:02d} AUDIO\n'.format(i+1)
			output += '    TITLE "{}"\n'.format(track.title)
			if self.cd_performer != track.performer: output += '    PERFORMER "{}"\n'.format(track.performer)
			if not one_file:
				output += '    FILE "{}" WAVE\n'.format(track.file)

			for idx in sorted(track.time.keys()):
				t = track.time[idx]
				#~ print t
				mins = t // (60*75)
				t -= mins * (60*75)
				sec = t // 75
				t -= sec * 75
				rest = t
				output += '    INDEX {:02d} {:02d}:{:02d}:{:02d}\n'.format(idx, int(mins), int(sec), rest)
		return output


	def __analyze_wave(self, trackfile):
		wafi = wave.open(trackfile, 'rb')
		param_names = ('nchannels', 'sampwidth', 'framerate', 'nframes', 'comptype', 'compname')
		params = wafi.getparams()
		param_dict = dict(zip(param_names, params))
		wafi.close()
		return param_dict, params


	def join(self, cue_obj, wave_filename=u'join'):
		self.current_file = wave_filename + u'.wav'
		wafo = wave.open(self.current_file, 'wb')
		set_params = True

		for i, track in enumerate(self.tracks):
			Decode(track.file)
			if set_params:
				set_params = False
				pdict, param = self.__analyze_wave(track.file)
				#~ print pdict['nframes'] / (pdict['framerate'] // 75)
				wafo.setparams(param)

			wafi = wave.open(track.file, 'rb')
			pdict, param = self.__analyze_wave(track.file)

			# calculate number of frames
			start = pdict['framerate'] * track.time.get(0, track.time[1]) // 75
			stop = pdict['nframes']
			if len(self.tracks) > i+1 and self.tracks[i+1].file == track.file:
				stop = pdict['framerate'] * self.tracks[i+1].time.get(0, self.tracks[i+1].time[1]) // 75
			print start, stop, pdict['nframes']
			wafi.setpos(start)
			wafo.writeframes(wafi.readframes(stop-start))
			wafi.close()

			track.file = self.current_file


		# second part
		time_offset = pdict['nframes']*75 // pdict['framerate']

		for i, track in enumerate(cue_obj.tracks):
			Decode(track.file)

			wafi = wave.open(track.file, 'rb')
			pdict, param = self.__analyze_wave(track.file)

			# calculate number of frames
			start = pdict['framerate'] * track.time.get(0, track.time[1]) // 75
			stop = pdict['nframes']
			if len(cue_obj.tracks) > i+1 and cue_obj.tracks[i+1].file == track.file:
				stop = pdict['framerate'] * cue_obj.tracks[i+1].time.get(0, cue_obj.tracks[i+1].time[1]) // 75
			print start, stop, pdict['nframes']
			wafi.setpos(start)
			wafo.writeframes(wafi.readframes(stop-start))
			wafi.close()

			track.file = self.current_file
			for key, value in cue_obj.tracks[i].time.iteritems():
				cue_obj.tracks[i].time[key] = value + time_offset

		self.tracks += cue_obj.tracks

		with open(wave_filename+u'.cue', 'w') as f:
			f.write( str(self) )



if __name__ == "__main__":
	cue_files = []
	for filename in os.listdir(u'.'):
		if os.path.isfile(filename) and filename.lower().endswith(u'.cue'):
			cue_files.append(filename)

	cue_objs = []
	joined_filename = None
	for f in sorted(cue_files):
		if not joined_filename: joined_filename = f
		else:
			for i, c in enumerate(f):
				if joined_filename[i] != c:
					joined_filename = joined_filename[:i]
					break

		cue = CueSheet(f)
		cue.read()
		cue_objs.append(cue)

	joined_filename = joined_filename.rstrip(u'CD').rstrip()
	#~ print joined_filename
	x = cue_objs[0].join(cue_objs[1], joined_filename)




