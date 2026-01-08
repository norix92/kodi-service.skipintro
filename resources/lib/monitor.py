# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from __future__ import absolute_import, division, unicode_literals
from xbmc import Monitor
from api import Api
from playbackmanager import PlaybackManager
from player import SkipIntroPlayer
from statichelper import to_unicode
from utils import decode_json, get_property, get_setting_bool, kodi_version_major, log as ulog


class SkipIntroMonitor(Monitor):
    """Service monitor for Kodi"""

    def __init__(self):
        """Constructor for Monitor"""
        self.player = SkipIntroPlayer()
        self.api = Api()
        self.playback_manager = PlaybackManager()
        Monitor.__init__(self)

    def log(self, msg, level=1):
        """Log wrapper"""
        ulog(msg, name=self.__class__.__name__, level=level)

    def run(self):  # pylint: disable=too-many-branches
        """Main service loop"""
        self.log('Service started', 0)

        while not self.abortRequested():
            # check every 1 sec
            if self.waitForAbort(1):
                # Abort was requested while waiting. We should exit
                break

            if not self.player.is_tracking():
                continue

            if bool(get_property('PseudoTVRunning') == 'True'):
                self.player.disable_tracking()
                self.playback_manager.demo.hide()
                continue

            if get_setting_bool('disableSkipIntro'):
                # Skip Intro is disabled
                self.player.disable_tracking()
                self.playback_manager.demo.hide()
                continue

            # Method isExternalPlayer() was added in Kodi v18 onward
            if kodi_version_major() >= 18 and self.player.isExternalPlayer():
                self.log('Skip Intro tracking stopped, external player detected', 2)
                self.player.disable_tracking()
                self.playback_manager.demo.hide()
                continue

            last_file = self.player.get_last_file()
            try:
                current_file = to_unicode(self.player.getPlayingFile())
            except RuntimeError:
                self.log('Skip Intro tracking stopped, failed player.getPlayingFile()', 2)
                self.player.disable_tracking()
                self.playback_manager.demo.hide()
                continue

            if (current_file.startswith((
                    'bluray://', 'dvd://', 'udf://', 'iso9660://', 'cdda://'))
                    or current_file.endswith((
                        '.bdmv', '.iso', '.ifo'))):
                self.log('Skip Intro tracking stopped, Blu-ray/DVD/CD playing', 2)
                self.player.disable_tracking()
                self.playback_manager.demo.hide()
                continue

            if last_file and last_file == current_file:
                # Already processed this playback before
                continue

            try:
                total_time = self.player.getTotalTime()
            except RuntimeError:
                self.log('Skip Intro tracking stopped, failed player.getTotalTime()', 2)
                self.player.disable_tracking()
                self.playback_manager.demo.hide()
                continue

            if total_time == 0:
                self.log('Skip Intro tracking stopped, no file is playing', 2)
                self.player.disable_tracking()
                self.playback_manager.demo.hide()
                continue

            try:
                play_time = self.player.getTime()
            except RuntimeError:
                self.log('Skip Intro tracking stopped, failed player.getTime()', 2)
                self.player.disable_tracking()
                self.playback_manager.demo.hide()
                continue

            self.player.set_last_file(current_file)

            self.playback_manager.launch_skip_intro()
            self.log('Skip Intro style autoplay succeeded', 2)
            self.player.disable_tracking()

        self.log('Service stopped', 0)

    def onNotification(self, sender, method, data):  # pylint: disable=invalid-name
        """Notification event handler for accepting data from add-ons"""
        if not method.endswith('skipintro_data'):  # Method looks like Other.skipintro_data
            return

        decoded_data, encoding = decode_json(data)
        if decoded_data is None:
            self.log('Received data from sender %s is not JSON: %s' % (sender, data), 2)
            return

        self.playback_manager.handle_demo()
        decoded_data.update(id='%s_play_action' % sender.replace('.SIGNAL', ''))
        self.api.addon_data_received(decoded_data, encoding=encoding)
        self.player.enable_tracking()
        self.player.reset_queue()
