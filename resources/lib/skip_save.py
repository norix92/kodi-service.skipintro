# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from utils import get_setting_bool, log as ulog, get_setting_int
import xbmcvfs,xbmc,xbmcaddon,json,os, re


class Skip_Save:
    addonInfo = xbmcaddon.Addon().getAddonInfo
    profilePath = xbmcvfs.translatePath(addonInfo('profile'))
    skipFile = os.path.join(profilePath, 'skipintro.json')
    defaultSkip = get_setting_int('defaultSkip')
    if not os.path.exists(profilePath): xbmcvfs.mkdir(profilePath)

    def log(self, msg, level=2):
        ulog(msg, name=self.__class__.__name__, level=level)
        
    def cleantitle(self, title):
        if title == None: return
        title = title.lower()
        title = re.sub('&#(\d+);', '', title)
        title = re.sub('(&#[0-9]+)([^;^0-9]+)', '\\1;\\2', title)
        title = title.replace('&quot;', '\"').replace('&amp;', '&')
        title = re.sub(r'\]*\>','', title)
        title = re.sub('\n|([[].+?[]])|([(].+?[)])|\s(vs|v[.])\s|(:|;|-|"|,|\'|\_|\.|\?)|\(|\)|\[|\]|\{|\}|\s', '', title).lower()
        return title.lower()
        
    def updateSkip(self, title, seconds=defaultSkip, start=0, service=True):
        with open(self.skipFile, 'r') as file:
             json_data = json.load(file)
             for item in json_data:
                   if self.cleantitle(item['title']) == self.cleantitle(title):
                      item['service'] = service
                      item['skip'] = seconds
                      item['start'] = start
        with open(self.skipFile, 'w') as file:
            json.dump(json_data, file, indent=2)
            
    def newskip(self, title, seconds, start=0):
        if seconds == '' or seconds == None: seconds = self.defaultSkip
        newIntro = {'title': title, 'service': True, 'skip': seconds, 'start': start}
        try:
            with open(self.skipFile) as f:
                data = json.load(f)
        except:
            data = []
        for item in data:
            if self.cleantitle(title) in self.cleantitle(item['title']):
                self.updateSkip(title, seconds=seconds, start=start, service=True)
                return
        data.append(newIntro)
        with open(self.skipFile, 'w') as f:
            json.dump(data, f, indent=2)
            
    def getSkip(self, title):
        try:
            with open(self.skipFile) as f:
                data = json.load(f)
            skip = [i for i in data if i['service'] != False]
            skip = [i['skip'] for i in skip if self.cleantitle(i['title']) == self.cleantitle(title)][0]
        except: 
            skip = self.defaultSkip
            self.newskip(title, skip)
        return  skip
        
    def checkService(self, title):
        try:
            with open(self.skipFile) as f: data = json.load(f)
            skip = [i['service'] for i in data if self.cleantitle(i['title']) == self.cleantitle(title)][0]
        except: skip = True
        return  skip

    def checkStartTime(self, title):
        try:
            with open(self.skipFile) as f: data = json.load(f)
            start = [i['start'] for i in data if self.cleantitle(i['title']) == self.cleantitle(title)][0]
        except: start = 0
        return  start
        
    if not os.path.exists(skipFile): newskip('default', self.defaultSkip)
