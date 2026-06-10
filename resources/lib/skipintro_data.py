# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from api_calls import Api_Calls
from skipintro_database import SkipIntro_Database
from utils import get_setting_bool, log as ulog, get_setting_int
import xbmcvfs,xbmc,xbmcaddon,os, re
import inspect

class SkipIntro_Data:
    defaultSkip = get_setting_int('defaultSkip', default=45)

    def __init__(self):
        #self.__dict__ = self._shared_state
        self.api_calls = Api_Calls()
        self.skipintro_database = SkipIntro_Database()

    def log(self, msg, level=2):
        method = inspect.currentframe().f_back.f_code.co_name
        msg = f"[{method}] {msg}"
        ulog(msg, name=self.__class__.__name__, level=level)
        
    def cleanTitle(self, title):
        pattern = r'''
            \n |
            (\[.+?\]) |
            (\(.+?\)) |
            \s(vs|v[.])\s |
            [:;"',._?\-] |
            [()\[\]{}] |
            \s
        '''
        if title == None: return
        title = title.lower()
        title = re.sub('&#(\d+);', '', title)
        title = re.sub('(&#[0-9]+)([^;^0-9]+)', '\\1;\\2', title)
        title = title.replace('&quot;', '\"').replace('&amp;', '&')
        title = re.sub(r'\]*\>','', title)
        title = re.sub(pattern, '', title, flags=re.VERBOSE).lower()
        return title.lower()
            
    def getIntroData(self, show_id, title, episode_id, season, episode):
        try:
            self.log('Trying to get show_data from SkipIntro Database.')
            show_item = self.skipintro_database.get_show(show_id)
            
            if show_item is None:
                self.log('Show not found in SkipIntro Database.')
                self.log('title %s' % title)
                imdb_id = self.api_calls.tvmaze_get_imdb_id_from_series(title)
                self.log('imdb_id %s' % imdb_id)
                self.skipintro_database.save_show(show_id, imdb_id, True, False, 0, self.defaultSkip)
                show_item = self.skipintro_database.get_show(show_id)
            self.log('show_item %s' % show_item)
            if show_item["use_show_data_only"] == 1:
                self.log('Returning show data from SkipIntro Database.')
                return show_item["intro_start"], show_item["intro_end"]
            else:
                self.log('Trying to episode data from SkipIntro Database.')
                if show_item["imdb_id"] is None:
                    imdb_id = self.api_calls.tvmaze_get_imdb_id_from_series(title) 
                    self.skipintro_database.save_show(show_id, imdb_id, show_item["active"], show_item["use_show_data_only"], show_item["intro_start"], show_item["intro_end"])
                    show_item = self.skipintro_database.get_show(show_id)
                
                episode_item = self.skipintro_database.get_episode(episode_id)
                if episode_item is None: 
                    self.log('Episode not found in SkipIntro Database.')
                    episode_data = self.api_calls.introdb_get_intro_data(show_item["imdb_id"], season, episode)
                    if not episode_data is None:
                        self.log('episode_data %s' % episode_data)
                        self.skipintro_database.save_episode(show_id, episode_id, episode_data["updated_at"], episode_data["intro_start"], episode_data["intro_end"], True)
                        return episode_data["intro_start"], episode_data["intro_end"]
                    else:
                        self.log('Episode not found in IntroDB. Returning show data.')
                        return show_item["intro_start"], show_item["intro_end"]
                else: 
                    if episode_item["active"] == 1:
                        self.log('Returning episode data from SkipIntro Database.')
                        return episode_item["intro_start"], episode_item["intro_end"]
                    
        except Exception as e:
            self.log('Error: %s' % e, 2)
            return None, None
        
    def getShowEnabled(self, show_id):
        try:
            self.log('Trying to get show_data from SkipIntro Database.')
            show_item = self.skipintro_database.get_show(show_id)
            
            if show_item is None:
                self.log('Show not found in SkipIntro Database.')
                return True
            else:
                self.log('show_item %s' % show_item)
                if show_item["active"] == 0:
                    self.log('Show_Enabled = False.')
                    return False
                else:
                    self.log('Show_Enabled = True')
                    return True
        except Exception as e:
            self.log('Error: %s' % e, 2)
            return True
