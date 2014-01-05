pyCueSheet
==========
Join and split audio files by cue sheets

The Problem
-----------
Some time ago my audio CD collection was _small_ enough to fit onto a new hard disc
if I use a lossless audio codec. So the plan was to re-rip all my CDs into a wave
file, create a cue sheet, split the wave file (for my portable player) and archive
the wave and cue file.

Ok, my preferred CD grabber is [EAC][]. It's able to do task number one (create
wave and cue file) without any pain but splitting by use of cue files is not working
as expected.

First of all it is slow, a lot to click and there is a playtime limit of 99 minutes.
Maybe you wonder why 99 minutes is a problem. Well there exists double cd albums
which I would like to join into a single wave and cue file.


The Solutions
-------------

### cuejoin.py
Joins two and more wave and cue files.
#### How to use it?
Well, copy the file into the folder of the CD images. Make sure that the images
are index. The script searches for a _CD\\d_ in the filename. As an example the
files of a double CD album: Porcupine Tree's The Incident

- Porcupine Tree - The Incident CD1.cue
- Porcupine Tree - The Incident CD1.wav
- Porcupine Tree - The Incident CD2.cue
- Porcupine Tree - The Incident CD2.wav

After execution of the script two more files were created

- Porcupine Tree - The Incident.cue
- Porcupine Tree - The Incident.wav

At this point we can go one step further: remove the sources (CD1 & CD2) and splitting
the file.


### cuesplit.py
Splits a wave file by a cue sheets. It creates as many codec process as CPUs exists.
#### How to use it?
Well, copy the file into the folder of the CD image and execute. But first you should
make your configuration. Most will need MP3 or Ogg Vorbis output format. You have to
configure the output to generate and there are a lot of possibilities. Modify the
following line.

	### modify me
	use_codecs = (mp3_enc, ogg_enc, mpc_enc, tta_enc )
	###


- mp3_enc: needs [LAME][]
- ogg_enc: needs [Ogg Vorbis][]
- flac_enc: needs [FLAC][]
- ape_enc: needs [Monkey's Audio][]
- tta_enc: needs [TTA][]
- mpc_enc: needs [Musepack][]
- wv_enc: needs [Wavpack][]

The script needs the command-line codec of each format. Either your system
has them already installed or you have to get them. Take a look at [Rarewares][].
There you can find executables of open-source audio codecs.

The script searches for _.cue_ files and wave files referenced by the cue file.
First, this wave file is splitted into smaller wave files. Afterwards the codec
is called. At the end you should get the desired files with this filename format:

	"<Track-Number> - <Track-Name>.<Ext>"

At the moment there is no different format possible because I don't like any
different format :)


Notice
------
Python 2.7 on Windows needed. Most likely it works with some small changes also
with 2.6 or 3.x and also on Linux and OSX.



[EAC]:http://www.exactaudiocopy.de/
[LAME]:http://lame.sourceforge.net/
[Ogg Vorbis]:(http://www.vorbis.com/
[FLAC]:https://xiph.org/flac/
[Monkey's Audio]:http://www.monkeysaudio.com/
[TTA]:http://en.true-audio.com/
[Musepack]:http://www.musepack.net/
[Wavpack]:http://www.wavpack.com/
[Rarewares]:http://www.rarewares.org
