# mud
Music Deduplicator - find sound file duplicates.

This is currently work in progress.

## Introduction
Basic file level deduplication is a common task and many tools exist to do this. Just for fun, I also 
wrote my own, you can find it in `dedup/dedup.py` (use `-h` to get help). 

But with sound files (most likely mp3s), which are possibly generated from other sources like CDs, you
might come across the situation that you have *similar* files. E.g. the same CD ripped twice, but with
different bitrate, or encoded with different encoders. The recording is still the same, and you probably
only need on copy of it. But just comparing the checksum of the file will fail, since the files are different
on a binary level. In order to recognize theses files as the same recording, audio fingerprinting is needed.
mud is basically a wrapper around [dejavu](https://github.com/worldveil/dejavu), which does the audio
fingerprinting. The author of dejavu also 
[explains](https://willdrevo.com/fingerprinting-and-audio-recognition-with-python.html) how the fingerprinting works.
(I enjoyed reading that :) )

mud (or rather dejavu) will also recognize identical files as such, but I would recommend to do a file
level deduplication first, as you are probably not interested in keeping multiple copies of the same
file. Then use mud to find similar files. mud will not move or delete similar files, since it is not
a priori clear which is the *good* copy. You will need to resolve that manually, e.g. by listening to the
files yourself.

## Installation
mud is currently developed on a fedora 21 server. It will probably also run on other recent distros,
though the `setup.sh` script is specific to the redhat familiy of distros.
After a basic OS installation (including git), clone this repo and run the `setup.sh` script: 

```
git clone git@github.com:shoubamzlibap/mud.git
cd mud
./setup.sh
```

The `setup.sh` script will install several packages via yum, and also some python packages via pip that
are not yet in the official fedora repos. 
`setup.sh` will create a database and a database user for mud and dejavu.
It also creates a `settings.py` file, which contains among others a variable called `music_base_dir`, which
should be set accordingly.

## Usage
Currently, mud is used via it's cli. For usage and available options, read the help message:

```
./mud.py -h
```

## Required Space for Database
The exact space requirement depends on various factors. The main contribution to disk usage
are the audio fingerprints. The ratio of sound file space on disk to fingerprints
depends on various factors, like the bit rate of your sound files and the
percentage of duplicates (duplicates will be fingerprinted only once). To get an upper bound on
space requrement, I would assume to have no duplicates. Then you will need about 35% (this number
is my first guess and will be updated with more experience) of your sound file disk space for the
fingerprints.

dejavu states that it needs about the same amount of disk space for the fingerprints as the original
audio files. mud needs less, as not the whole audio file is fingerprinted, but only the first 30 seconds.
This value can be altered in settings.py (`fingerprint_limit`) to save even more disk space. dejavu claims
that usually 5 seconds are enough to recognize a song. I have chosen 30 seconds as a default in order
to account for songs with long intros, where not much significant is happening.

