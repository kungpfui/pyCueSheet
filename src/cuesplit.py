#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# $Id: cuesplit.py 1692 2014-07-16 21:47:34Z Stefan $

import os, sys, re
import time
import wave
import subprocess
import multiprocessing


def ogg_enc(queue, trackfilename, track, quality=5):
	"""Ogg Vorbis encoder."""
	subprocess.call(['oggenc2',
		'-q', str(quality),
		'-a', track.performer,
		'-N', track.index,
		'-t', track.title,
		'-d', track.cd_date,
		'-G', track.cd_genre,
		'-l', track.cd_title,
		trackfilename,
	] )
	# remove a token
	queue.get()

def opus_enc(queue, trackfilename, track, quality=112.0):
	"""Opus encoder."""
	param = ['opusenc',
		'--vbr',
		'--bitrate', str(quality),
		#'--comp', 10, #default
		#'--framesize', '60', # default 20
		'--artist', track.performer,
		'--comment', 'tracknumber={}'.format(track.index),
		'--title', track.title,
		'--date', track.cd_date,
		'--genre', track.cd_genre,
		'--album', track.cd_title,
		trackfilename,
		'{}.opus'.format( os.path.splitext(trackfilename)[0] ),
	]
	subprocess.call(param)
	# remove a token
	queue.get()


def mp3_enc(queue, trackfilename, track, quality=5):
	"""MPEG2-Layer3 encoder."""
	subprocess.call(['lame',
		'-h',
		'-V', str(quality), # variable bitrate
		'--ta', track.performer,
		'--tn', track.index,
		'--tt', track.title,
		'--ty', track.cd_date,
		'--tg', track.cd_genre,
		'--tl', track.cd_title,
		trackfilename,
		'{}.mp3'.format( os.path.splitext(trackfilename)[0] ),
	] )
	# remove a token
	queue.get()

def flac_enc(queue, trackfilename, track, quality='--best'):
	"""FLAC encoder."""
	subprocess.call(['flac',
		quality,
		'--tag=performer={}'.format(track.performer),
		'--tag=album={}'.format(track.cd_title),
		'--tag=index={}'.format(track.index),
		'--tag=track={}'.format(track.title),
		'--tag=date={}'.format(track.date),
		'--tag=genre={}'.format(track.genre),
		trackfilename,
		'>{}.flac'.format( os.path.splitext(trackfilename)[0] ),
	] )
	# remove a token
	queue.get()

def ape_enc(queue, trackfilename, track, quality=3000):
	"""Monkey's Audio encoder."""
	subprocess.call(['mac',
		trackfilename,
		'{}.ape'.format( os.path.splitext(trackfilename)[0] ),
		'-c{}'.format(quality),
	] )
	# remove a token
	queue.get()


def tta_enc(queue, trackfilename, track, quality=None):
	"""True Audio encoder."""
	subprocess.call(['ttaenc',
		'-e',
		trackfilename,
		'.',
	] )
	# remove a token
	queue.get()

def wv_enc(queue, trackfilename, track, quality=None):
	"""Wavepack encoder."""
	subprocess.call(['wavpack',
		trackfilename,
		'.',
	] )
	# remove a token
	queue.get()

def mpc_enc(queue, trackfilename, track, quality=5.0):
	"""Musepack encoder."""
	subprocess.call(['mppenc',
		'--quality', '{}'.format(quality),
		trackfilename,
	] )
	# remove a token
	queue.get()


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
		return float(t[0])*60 + float(t[1]) + float(t[2]) / 75.0


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
			start = int(param_dict['framerate'] * track.time[1])
			stop = param_dict['nframes']
			if len(self.tracks) > i+1 and self.tracks[i+1].file == track.file:
				stop = int(param_dict['framerate'] * self.tracks[i+1].time.get(0, self.tracks[i+1].time[1]))


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




if __name__ == "__main__":
	### modify me
	use_codecs = (mp3_enc, opus_enc, ogg_enc, mpc_enc, tta_enc )
	###

	cue_files = []
	for filename in os.listdir(u'.'):
		if os.path.isfile(filename) and filename.lower().endswith(u'.cue'):
			cue_files.append(filename)

	for f in cue_files:
		cue = CueSheet(f)
		cue.read()
		cue.split( use_codecs )


