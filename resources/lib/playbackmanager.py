# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from __future__ import absolute_import, division, unicode_literals
from xbmc import sleep
from api import Api
from api_calls import Api_Calls
from skipintro_data import SkipIntro_Data
from demo import DemoOverlay
from player import SkipIntroPlayer
from playitem import PlayItem
from state import state
from skipintro import SkipIntro
from utils import addon_path, calculate_progress_steps, clear_property, event, get_setting_bool, get_setting_int, log as ulog, set_property
import inspect

class PlaybackManager:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state
        self.api = Api()
        self.play_item = PlayItem()
        self.skipintro_data = SkipIntro_Data()
        self.api_calls = Api_Calls()
        self.player = SkipIntroPlayer()
        self.demo = DemoOverlay(12005)
        self.intro_start = None
        self.intro_end = None

    def log(self, msg, level=2):
        method = inspect.currentframe().f_back.f_code.co_name
        msg = f"[{method}] {msg}"
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

        if intro_page.is_cancel() or not skipIntro:
            return
        
        self.log('Skipping Intro', 2)
        #if source == 'playlist' or state.queued:
            # Skip in playlist media
        #elif self.api.has_addon_data():
            # Play add-on media
        #    self.api.play_addon_item()
        #else:

        if not self.intro_end is None and self.intro_end > 0:
            if self.player.isPlayingVideo():
                self.log('Skipping in player.')
                self.player.seekTime(float(self.intro_end))
            else:
                self.log('Skipping with API.')
                player_id = self.api._get_playerid(playerid_cache=[None])
                
                if player_id is not None:
                    self.api.skip(player_id, self.intro_end)
        
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
        
        show_enabled = self.skipintro_data.getShowEnabled(state.show_id)
        showPopupIfDisabled = get_setting_bool('showPopupIfDisabled') 

        if not show_enabled and not showPopupIfDisabled:
            self.log('Show disabled. Not showing popup.', 2)
            return False, False
           
        self.intro_start, self.intro_end = self.skipintro_data.getIntroData(state.show_id, state.show_title, state.show_episode_id, state.show_season, state.show_episode)
        if self.intro_start is None:
            self.intro_start = 0
            
        self.log('intro_start: %s seconds.' % self.intro_start)
        self.log('intro_end: %s seconds.' % self.intro_end)
        
        last_time = self.player.getTime()    
        while (self.player.isPlaying() and (self.intro_start - play_time > 1)):
            try:
                play_time = self.player.getTime()
            except RuntimeError:
                if showing_intro_page:
                    intro_page.close()
                    showing_intro_page = False
                break
                
            if play_time > self.intro_end:
                self.log("Intro over.")
                return False, False
                
            last_time = play_time
            waiting_time = self.intro_start - play_time
            self.log('Wating %s seconds until SkipIntro popup appears' % waiting_time)
            sleep(100)
            
        progress_step_size = calculate_progress_steps(total_time - play_time)
        intro_page.set_item(episode)
        intro_page.set_progress_step_size(progress_step_size)

        showing_intro_page = False
        intro_page.show()
        set_property('service.skipintro.dialog', 'true')
        showing_intro_page = True
        notification_time = get_setting_int('notificationTime') 
        
        if (self.intro_start == 0):
            notification_time = notification_time + 2

        while (self.player.isPlaying() and (notification_time + self.intro_start - play_time > 1) 
               and not intro_page.is_cancel() and not intro_page.is_skip_intro()):
            try:
                play_time = self.player.getTime()
                total_time = self.player.getTotalTime()
            except RuntimeError:
                if showing_intro_page:
                    intro_page.close()
                    showing_intro_page = False
                break

            remaining = notification_time + self.intro_start - play_time
            if not state.pause:
                if showing_intro_page:
                    intro_page.update_progress_control(remaining=remaining, runtime=total_time)
            sleep(100)

        autoSkipMode = get_setting_int('autoSkipMode')     
        if not show_enabled and showPopupIfDisabled:
            self.log('Show disabled. Showing popup.', 2)
            return True, False
            
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
