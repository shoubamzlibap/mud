"""
mud_gui.py

Currently just a poc - a gui to review the doublers.
"""

"""
#TODO:
* get ip from server, but allow as argument
* get rid of global variables
* give message if no more songs in queue
* create AudioPlayer from common class of VideoPlayer
"""

# a place to move duplicates to
DUPES_DIR = '/var/tmp/dups'

import argparse
import remi.gui as gui
from remi import start, App
from remi import Widget
from remi.gui import decorate_constructor_parameter_types, decorate_set_on_listener, VideoPlayer
import pickle
from pprint import pprint
from multiprocessing import Process
from multiprocessing import Queue as MPQueue
import socket
import sys
import logging
import settings
import mud
from dedup import dedup

queue = MPQueue()
logger = logging.getLogger('mud_gui')
logger.setLevel(logging.DEBUG)

class AudioPlayer(Widget):
    # some constants for the events
    EVENT_ONENDED = 'onended'

    @decorate_constructor_parameter_types([str, str, bool, bool])
    def __init__(self, audio, poster=None, autoplay=False, loop=False, **kwargs):
        super(AudioPlayer, self).__init__(**kwargs)
        logger.debug('Creating Audio player for ' + audio)
        self.type = 'audio'
        self.attributes['src'] = audio
        self.attributes['preload'] = 'auto'
        self.attributes['type'] = 'audio/mpeg' # maybe this should be set according to file ending ...
        self.attributes['controls'] = None
        self.attributes['poster'] = poster
        self.set_autoplay(autoplay)
        self.set_loop(loop)

    def set_autoplay(self, autoplay):
        if autoplay:
            self.attributes['autoplay'] = 'true'
        else:
            self.attributes.pop('autoplay', None)

    def set_loop(self, loop):
        """Sets the VideoPlayer to restart video when finished.

        Note: If set as True the event onended will not fire."""

        if loop:
            self.attributes['loop'] = 'true'
        else:
            self.attributes.pop('loop', None)

    def onended(self):
        """Called when the media has been played and reached the end."""
        return self.eventManager.propagate(self.EVENT_ONENDED, ())

    @decorate_set_on_listener("onended", "(self,emitter)")
    def set_on_ended_listener(self, callback, *userdata):
        """Registers the listener for the VideoPlayer.onended event.

        Note: the listener prototype have to be in the form on_video_ended(self, widget).

        Args:
            callback (function): Callback function pointer.
        """
        self.attributes['onended'] = "sendCallback('%s','%s');" \
            "event.stopPropagation();event.preventDefault();" % (self.identifier, self.EVENT_ONENDED)
        self.eventManager.register_listener(self.EVENT_ONENDED, callback, *userdata)


class MudConnector(object):
    """Connect to the mud database"""

    def __init__(self, inst_num=0):
        """
        Create a mud object for getting duplicates

        inst_nume: integer, the mud instance number
        """
        logger.debug('Creating MudConnector')
        self.inst_num = inst_num

    def __enter__(self):
        """
        Start another process to fetch stuff from the database
        """
        logger.debug('Spawning process for mud connection')
        self.process = Process(target=mud.fill_dupes, args=(self.inst_num, queue))
        self.process.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        logger.debug('Stopping process for mud connection')
        self.process.join()


def get_dup():
    """
    Return a dup thingy

    """
    logger.debug('Getting a dup item of the queue')
    files_from_q = queue.get()
    if not files_from_q: return None
    files = []
    for song_file in files_from_q:
        files.append({
            'file': song_file['file_path'],
            })
    return {
        'files': files,
        'reviewed': False,
    }

class MudGui(App):
    def __init__(self, *args):
	self.static_path = settings.music_base_dir
        super(MudGui, self).__init__(*args, static_file_path=self.static_path)
        logger.debug('MudGui created')

    def main(self):
        logger.debug('Inside MudGui.main')

        # returning the root widget
        self.verticalContainer = gui.Widget(width=600)
        #self.verticalContainer = gui.VBox(width=600)
        #container = gui.VBox(width = 120, height = 100)

        self.verticalContainer.style['display'] = 'block'
        self.verticalContainer.style['overflow'] = 'hidden'

        # control at the bottom
        self.subcontainerBottom = horizontal_container()
        self.done_bt = self._simple_button('Done')
        self.skip_bt = self._simple_button('Skip')
        self.subcontainerBottom.append(self.done_bt)
        self.subcontainerBottom.append(self.skip_bt)
        
        self.verticalContainer.append(self.dup_container(), key='duplicates')
        self.verticalContainer.append(self.subcontainerBottom, key='bottom_control')

       # returning the root widget
        return self.verticalContainer

    def dup_container(self):
        """Return a list of containers"""
        dupContainer = horizontal_container()
        self.dup_set = get_dup()
        if not self.dup_set: return dupContainer
        i = 0;
        for song in self.dup_set['files']:
            dupContainer.append(self.song_container(song), key=str(i))
            i += 1
        return dupContainer

    def song_container(self, song):
        """
        Create a container for a song file

        song: dict, containing 'file', ...
        """
        song_container = horizontal_container()
        label = gui.Label(song['file'], width=250, height=50)
        check = gui.CheckBoxLabel('keep', False, width=60, height=90)
        check.style['margin'] = '10px'
	partial_song_path = '/res' + song['file'].replace(self.static_path, '')
	#TODO: check if partial song_path starts with a '/'
	import urllib
	partial_song_path = urllib.quote(partial_song_path)	
        audio = AudioPlayer(partial_song_path, width=120, height=30)
        audio.style['margin'] = '10px'
        song_container.append(check, key='check')
        song_container.append(audio, key='audio')
        song_container.append(label, key='label')
        return song_container

    def _simple_button(self, name):
        """
        Create and return a simple blutton and register the on click listener name.lower() + '_button_pressed'

        name: str, as it appears on the button

        """
        logger.debug('Creating _simple_button with name "' + name + '"')
        button = gui.Button(name, width=150, height=30)
        button.style['margin'] = '10px'
        listener_name = name.lower() + '_button_pressed'
        listener_func = getattr(self, listener_name)
        button.set_on_click_listener(listener_func)
        return button

    def done_button_pressed(self, widget):
        logger.debug('Done button pressed')
        dup_cont = self.verticalContainer.get_child('duplicates')
        song_containers = []
        reviewed = False
        i = 0
        while i < len(self.dup_set['files']):
            song_container = dup_cont.get_child(str(i))
            check = song_container.get_child('check')
            self.dup_set['files'][i]['keep'] = check.get_value()
            if check.get_value(): reviewed = True
            i += 1
        self.dup_set['reviewed'] = reviewed
        pprint(self.dup_set)
        self.move_files()
        if reviewed: self.next_dupset()
        else: pass # emit message like "use 'Next' if you don't want to decide right now"

    def skip_button_pressed(self, widget):
        logger.debug('Skip button pressed')
        pprint(self.dup_set)
        self.next_dupset()

    def next_dupset(self):
        """Get the next set of dups"""
        logger.debug('MyApp.next_dupset called')
        self.verticalContainer.append(self.dup_container(), key='duplicates')
        self.verticalContainer.append(self.subcontainerBottom, key='bottom_control')

    def move_files(self):
        """
        Move files that were not chosen to be kept
        """
        if not self.dup_set['reviewed']: return
        for song in self.dup_set['files']:
            if song['keep']: continue
            logger.debug('Moving ' + song['file'] + ' to ' + dedup.dir_dupes_target)
            #dedup.dir_dupes_target = '/var/tmp'
            dedup.move_files([song['file'],])
        
def horizontal_container():
    """Create a default horizontal container"""
    horizontalContainer = gui.Widget(width='100%')
    horizontalContainer.set_layout_orientation(gui.Widget.LAYOUT_HORIZONTAL)
    horizontalContainer.style['display'] = 'block'
    horizontalContainer.style['overflow'] = 'auto'
    horizontalContainer.style['margin'] = '0px'
    return horizontalContainer       

def guess_ip():
    """Guess IP to listen on"""
    return socket.gethostbyname(socket.gethostname())

def parse_cli_args():
    """
    Parse cli args and return an object with the given args
    """
    parser = argparse.ArgumentParser(
        description='Start web gui to present and discard the found doubles.')
    guessed_ip = guess_ip()
    parser.add_argument('-i', '--ip-address',
                        type=str,
                        default=guessed_ip,
                        help='The ip address to listen on. Defaults to ' + guessed_ip)
    return parser.parse_args()


def main():
    """The main function"""
    cli_args = parse_cli_args()
    dedup.simulate = True
    dedup.dir_with_dupes = settings.music_base_dir
    dedup.dir_dupes_target = DUPES_DIR
    with MudConnector() as mud_connector:
        start(MudGui, debug=True, address='10.23.23.53', port=8000, websocket_port=8001, start_browser=False)
        #start(MudApp, debug=True, address='10.23.23.53', port=8000, websocket_port=8001, start_browser=False,username='isaac', password='xxxxx' )

if __name__ == '__main__':
    main()
