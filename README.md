# mud
Music Deduplicator - find sound file duplicates.

## Introduction
Basic file level deduplication is a common task and many tools exist to do this. Just for fun, I also 
wrote my own, you can find it in `dedup/dedup.py` (use `-h` to get help). 

But with sound files (most likely mp3s), which are possibly generated from other sources like CDs, you
might come across the situation that you have *similar* files. E.g. the same CD ripped twice, but with
different bitrate, or encoded with different encoders. The recording is still the same, and you probably
only need one copy of it. But just comparing the checksum of the file will fail, since the files are different
on a binary level. In order to recognize theses files as the same recording, audio fingerprinting is needed.
mud is basically a wrapper around [dejavu](https://github.com/worldveil/dejavu), which does the audio
fingerprinting. The author of dejavu also 
[explains](https://willdrevo.com/fingerprinting-and-audio-recognition-with-python.html) how the fingerprinting works.
(I enjoyed reading that :) )

mud (or rather dejavu) will also recognize identical files as such, but I would recommend to do a file
level deduplication first, as you are probably not interested in keeping multiple copies of the same
file. Also, it is much faster. Then use mud to find similar files. mud will not move or delete similar files, since it is not
a priori clear which is the *good* copy. You will need to resolve that manually, e.g. by listening to the
files yourself.

## Installation
mud developement started on a fedora 21 server, and is currently on fedora 23. 
It will probably also run on other recent distros,
though the `setup.sh` script is specific to the redhat familiy of distros.
After a basic OS installation (including git), clone this repo and run the `setup.sh` script: 

```
git clone git@github.com:shoubamzlibap/mud.git
cd mud
./setup.sh
```

The `setup.sh` script will install several packages via yum, and also some python packages via pip that
are not yet in the official fedora repos. 
`setup.sh` will create databases and database users for mud and dejavu.
It also creates a `settings.py` file, which contains among others a variable called `music_base_dir`, which
should be set accordingly.

## Usage
Currently, mud is used via it's cli. For usage and available options, read the help message:

```
./mud.py -h
```

## Large collections and multiple instances
With "large", I refere to a collection that will take a long time to process, possibly weeks 
or months. If you ran `setup.sh`, scanned and build your collection and you got your
duplicates with no false positives in an acceptable amount of time, you can skip this section.

The processing time needed depends on a number of factors, among others:
    * Number of files (obviously)
    * Duration of fingerprint (see `fingerprint_limit` in `settings.py`)
    * Available hardware resources, mostly amount of RAM, disk and CPU speed to a lesser extent

If you look at `settings.py`, you will notice that there are multiple dejavu configs. The
reason for this will be explained below, but notice that they differ in the `fingerprint_limit`
setting. This is the time in seconds that dejavu will "listen" to the song in order to
fingerprint it. So for precise recognition a high value is good. But a high fingerprint value
will increase disk usage and slow down processing speed. So for your collection, you must find
out that sweet spot between enough precision and aceptable speed.
As a rough guess, this value will be somewhere between 5 and 30.

I used a `fingerprint_limit` value of 7 for a collection of about 100.000 files, and a 3GHz CPU with 2GB RAM took
about 2 Months to process the collection (8GB of RAM would probably do wonders here). 
Whew. And when it was finished, I got quite a few
false positives. So I should have increased the `fingerprint_limit` setting, needing even more
processing time. And indeed, that is what must be done, but not for the whole collection, just
for the possible duplicates. 

This is where "instances" enter the stage. There is a "primary"
instance, which is the default and must be used for the first scan and collection built.
Now if you get false positives but don't want to do the whole collection building again 
with a higher `fingerprint_limit`, you can use a secondary instance, which you can fill (`-f`) with
the "duplicates" from the primary instance. You can then use a higher `fingerprint_limit` on
that instance to get more accurate results. 

By default three instances are created, and you can fill the Nth instance with the duplicates from
instance no N-1. You can add even more instances by extending `dejavu_configs`, and manually
creating those databses. Or you hack `setup.sh` and change `num_dbs=3` to whatever you want. Though
I currently doubt that more then three instances will ever make sense. 

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


## mud gui
`mud_gui.py` is not really functional yet, it is in development.
It makes use of [remi](https://github.com/dddomodossola/remi) as a gui library. Since remi is not yet api stable,
I have added a snapshot of remi so that I can ensure `mud_gui.py` is compatible with the bundled remi version.
