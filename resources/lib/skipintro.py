# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from __future__ import absolute_import, division, unicode_literals
from datetime import datetime, timedelta
from platform import machine
from xbmc import Player
from xbmcgui import WindowXMLDialog
from statichelper import from_unicode
from api_calls import Api_Calls
from skipintro_database import SkipIntro_Database
from state import state
from utils import get_setting_bool, localize, localize_time, log as ulog
import inspect
import xbmcvfs,xbmc,xbmcaddon,json,os,xbmcgui, time, re

ACTION_PLAYER_STOP = 13
ACTION_NAV_BACK = 92
OS_MACHINE = machine()


class SkipIntro(WindowXMLDialog):
    item = None
    cancel = False
    skipIntro = False
    progress_step_size = 0
    current_progress_percent = 100

    def __init__(self, *args, **kwargs):
        self.action_exitkeys_id = [10, 13]
        self.progress_control = None
        self.api_calls = Api_Calls()
        self.skipintro_database = SkipIntro_Database()
        
        if OS_MACHINE[0:5] == 'armv7':
            WindowXMLDialog.__init__(self)
        else:
            WindowXMLDialog.__init__(self, *args, **kwargs)

    def onInit(self):  # pylint: disable=invalid-name
        #self.set_info()
        self.prepare_progress_control()
        self.getControl(3013).setLabel(localize(30002))  # Close
            
    def log(self, msg, level=2):
        method = inspect.currentframe().f_back.f_code.co_name
        msg = f"[{method}] {msg}"
        ulog(msg, name=self.__class__.__name__, level=level)

    def set_info(self):
        episode_info = '{season}x{episode}.'.format(**self.item)
        if self.item.get('rating') is None:
            rating = ''
        else:
            rating = str(round(float(self.item.get('rating')), 1))

        if self.item is not None:
            self.setProperty('tvshowtitle', self.item.get('showtitle', ''))
            self.setProperty('episode', str(self.item.get('episode', '')))
            self.setProperty('runtime', str(self.item.get('runtime', '')))

    def prepare_progress_control(self):
        try:
            self.progress_control = self.getControl(3014)
        except RuntimeError:  # Occurs when skin does not include progress control
            pass
        else:
            self.progress_control.setPercent(self.current_progress_percent)  # pylint: disable=no-member,useless-suppression

    def set_item(self, item):
        self.item = item

    def set_progress_step_size(self, progress_step_size):
        self.progress_step_size = progress_step_size

    def update_progress_control(self, remaining=None, runtime=None):
        self.current_progress_percent = self.current_progress_percent - self.progress_step_size
        try:
            self.progress_control = self.getControl(3014)
        except RuntimeError:  # Occurs when skin does not include progress control
            pass
        else:
            self.progress_control.setPercent(self.current_progress_percent)  # pylint: disable=no-member,useless-suppression

        if remaining:
            self.setProperty('remaining', from_unicode('%02d' % remaining))
        if runtime:
            self.setProperty('endtime', from_unicode(localize_time(datetime.now() + timedelta(seconds=runtime))))

    def set_cancel(self, cancel):
        self.cancel = cancel

    def is_cancel(self):
        return self.cancel

    def set_skip_intro(self, skipIntro):
        self.skipIntro = skipIntro

    def is_skip_intro(self):
        return self.skipIntro

    def onFocus(self, controlId):  # pylint: disable=invalid-name
        pass

    def doAction(self):  # pylint: disable=invalid-name
        pass

    def closeDialog(self):  # pylint: disable=invalid-name
        self.close()

    def onClick(self, controlId):  # pylint: disable=invalid-name
        if controlId == 3012:  # Skip Intro
            self.set_skip_intro(True)
            self.close()
        elif controlId == 3013:  # Close / Stop
            self.set_cancel(True)
            self.close()
        elif controlId == 3015:  # More
            show_item = self.skipintro_database.get_show(state.show_id)
            
            if not show_item is None:
                show_active = show_item["active"]
                use_show_data_only = show_item["use_show_data_only"]
            else:
                show_active = 1
                use_show_data_only = 0
                
            if show_active == 1:
                active_text = localize(30010)
                show_active_new = False
            else:
                active_text = localize(30009)
                show_active_new = True
                
            if use_show_data_only == 1:
                use_show_data_text = localize(30012)
                use_show_data_only_new = False
            else:
                use_show_data_text = localize(30011)
                use_show_data_only_new = True
                
            options = [
                localize(30013),
                localize(30014),
                localize(30015),
                use_show_data_text,
                localize(30008).format(active_text),
                localize(30017)
            ]
            
            selection = xbmcgui.Dialog().select("SkipIntro", options)
            
            if selection == 0: # Update show data
                dialog = xbmcgui.Dialog()
                
                show_item = self.skipintro_database.get_show(state.show_id)
                intro_start = show_item["intro_start"]
                intro_end = show_item["intro_end"]
                intro_start = dialog.input(localize(30039), defaultt=str(intro_start), type=xbmcgui.INPUT_NUMERIC)
                intro_end = dialog.input(localize(30038), defaultt=str(intro_end), type=xbmcgui.INPUT_NUMERIC)
                
                if intro_start == '' or intro_start == None: 
                    intro_start = 0
                if str(intro_end) != '' and str(intro_end) != '0': 
                    self.skipintro_database.save_show(state.show_id, show_item["imdb_id"], show_item["active"], use_show_data_only_new, intro_start, intro_end)
                    
                self.set_cancel(True)
            elif selection == 1: # Change episode data (API)
                show_item = self.skipintro_database.get_show(state.show_id)
                if not show_item is None:
                    episode_data = self.api_calls.introdb_get_intro_data(show_item["imdb_id"], state.show_season, state.show_episode)
                    if not episode_data is None:
                        self.log('episode_data %s' % episode_data)
                        self.skipintro_database.save_episode(state.show_id, state.show_episode_id, episode_data["updated_at"], episode_data["intro_start"], episode_data["intro_end"], True)
                self.set_cancel(True)
            elif selection == 2: # Change episode data
                dialog = xbmcgui.Dialog()
                
                show_item = self.skipintro_database.get_show(state.show_id)
                episode_item = self.skipintro_database.get_episode(state.show_episode_id)
                if episode_item is None:
                    intro_start = show_item["intro_start"]
                    intro_end = show_item["intro_end"]
                    updated_at = None
                else:
                    intro_start = episode_item["intro_start"]
                    intro_end = episode_item["intro_end"]
                    updated_at = episode_item["updated_at"]
                    
                intro_start = dialog.input(localize(30039), defaultt=str(intro_start), type=xbmcgui.INPUT_NUMERIC)
                intro_end = dialog.input(localize(30038), defaultt=str(intro_end), type=xbmcgui.INPUT_NUMERIC)
                
                if intro_start == '' or intro_start == None: 
                    intro_start = 0
                if str(intro_end) != '' and str(intro_end) != '0': 
                    self.skipintro_database.save_episode(state.show_id, state.show_episode_id, updated_at, intro_start, intro_end, True)
                    
                self.set_cancel(True)
            elif selection == 3: # Use Show value
                self.skipintro_database.save_show(state.show_id, show_item["imdb_id"], show_item["active"], use_show_data_only_new, show_item["intro_start"], show_item["intro_end"])
            elif selection == 4: # deactivate SkipIntro for this show
                self.skipintro_database.save_show(state.show_id, show_item["imdb_id"], show_active_new, show_item["use_show_data_only"], show_item["intro_start"], show_item["intro_end"])
                self.set_cancel(True)
            elif selection == 5: # delete show
                self.delete_show(state.show_id, state.show_title)
                self.set_cancel(True)
                self.close()
            self.close()

    def onAction(self, action):  # pylint: disable=invalid-name
        if action == ACTION_PLAYER_STOP:
            self.close()
        elif action == ACTION_NAV_BACK:
            self.set_cancel(True)
            self.close()
    
    def delete_show(self, show_id, show_title):
        dialog = xbmcgui.Dialog()
            
        # Confirmation
        if not dialog.yesno(
            localize(30005),
            localize(30006).format(show_title)
        ):
            return

        self.skipintro_database.delete_show(show_id, True)

        dialog.notification(
            'Skip Intro',
            localize(30007),
            xbmcgui.NOTIFICATION_INFO,
            3000
        )