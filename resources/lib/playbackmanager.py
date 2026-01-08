# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from __future__ import absolute_import, division, unicode_literals
from xbmc import sleep
from api import Api
from skip_save import Skip_Save
from demo import DemoOverlay
from player import SkipIntroPlayer
from playitem import PlayItem
from state import State
from skipintro import SkipIntro
from utils import addon_path, calculate_progress_steps, clear_property, event, get_setting_bool, get_setting_int, log as ulog, set_property


class PlaybackManager:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state
        self.api = Api()
        self.play_item = PlayItem()
        self.skip_save = Skip_Save()
        self.state = State()
        self.player = SkipIntroPlayer()
        self.demo = DemoOverlay(12005)

    def log(self, msg, level=2):
        ulog(msg, name=self.__class__.__name__, level=level)

    def handle_demo(self):
        if get_setting_bool('enableDemoMode'):
            self.log('Skip Intro DEMO mode enabled, skipping automatically to the end', 0)
            self.demo.show()
            try:
                total_time = self.player.getTotalTime()
                self.player.seekTime(total_time - 15)
            except RuntimeError as exc:
                self.log('Failed to seekTime(): %s' % exc, 0)
        else:
            self.demo.hide()

    def launch_skip_intro(self):
        enable_playlist = get_setting_bool('enablePlaylist')
        episode, source = self.play_item.get_episode()
        self.log('Playlist setting: %s' % enable_playlist)
        if source == 'playlist' and not enable_playlist:
            self.log('Playlist integration disabled', 2)
            return
        if not episode:
            # No episode get out of here
            self.log('Error: no episode could be found to skip...exiting', 1)
            return
            
        self.log('Launch Skip Intro')
        self.launch_popup(episode, source)
        
        self.api.reset_addon_data()

    def launch_popup(self, episode, source=None):
        intro_page = SkipIntro('script-skipintro.xml', addon_path(), 'default', '1080i')
        showing_intro_page, skipIntro = self.show_popup_and_wait(intro_page, episode)

        if not showing_intro_page or not skipIntro:
            return 
            
        self.log('Skipping Intro', 2)
        #if source == 'playlist' or self.state.queued:
            # Skip in playlist media
        #elif self.api.has_addon_data():
            # Play add-on media
        #    self.api.play_addon_item()
        #else:
        player_id = self.api._get_playerid(playerid_cache=[None])
        self.log('State show_title: %s' % self.state.show_title)
        skip_duration = int(self.skip_save.getSkip(title=self.state.show_title))
        self.api.skip(player_id, skip_duration)
            
        return
    def show_popup_and_wait(self, intro_page, episode):
        if self.player.getTime() > 2:
            return False, False
        try:
            play_time = self.player.getTime()
            total_time = self.player.getTotalTime()
        except RuntimeError:
            self.log('exit early because player is no longer running', 2)
            return False, False
        
        is_disabled = self.skip_save.checkService(title=self.state.show_title)
        if not is_disabled: 
            return False, False
        
        start_time = int(self.skip_save.checkStartTime(title=self.state.show_title))
        while (self.player.isPlaying() and (start_time - play_time > 1)):
            try:
                play_time = self.player.getTime()
            except RuntimeError:
                if showing_intro_page:
                    intro_page.close()
                    showing_intro_page = False
                break
            waiting_time = start_time - play_time
            self.log('Wating %s seconds...' % waiting_time)
            sleep(100)
        progress_step_size = calculate_progress_steps(total_time - play_time)
        intro_page.set_item(episode)
        intro_page.set_progress_step_size(progress_step_size)

        showing_intro_page = False
        intro_page.show()
        set_property('service.skipintro.dialog', 'true')
        showing_intro_page = True
        notification_time = get_setting_int('notificationTime') 
        if (start_time == 0):
            notification_time = notification_time + 2

        while (self.player.isPlaying() and (notification_time + start_time - play_time > 1) 
               and not intro_page.is_cancel() and not intro_page.is_skip_intro()):
            try:
                play_time = self.player.getTime()
                total_time = self.player.getTotalTime()
            except RuntimeError:
                if showing_intro_page:
                    intro_page.close()
                    showing_intro_page = False
                break

            remaining = notification_time + start_time - play_time
            if not self.state.pause:
                if showing_intro_page:
                    intro_page.update_progress_control(remaining=remaining, runtime=total_time)
            sleep(100)

        autoSkipMode = get_setting_int('autoSkipMode')       
        if showing_intro_page and intro_page.is_skip_intro():
            return True, True
        elif showing_intro_page and not intro_page.is_skip_intro() and autoSkipMode == 0:
            return True, True
        else:
            return True, False

    def extract_play_info(self, intro_page, showing_intro_page):
        if showing_intro_page:
            intro_page.close()
            should_play_default = not intro_page.is_cancel()
            should_play_non_default = intro_page.is_watch_now()
        else:
            # FIXME: This is a workaround until we handle this better (see comments in #142)
            return False, False

        clear_property('service.skipintro.dialog')
        return should_play_default, should_play_non_default
