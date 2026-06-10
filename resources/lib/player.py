# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from __future__ import absolute_import, division, unicode_literals
from xbmc import getCondVisibility, Player, Monitor
from api import Api
from state import state

class SkipIntroPlayer(Player):
    """Service class for playback monitoring"""
    last_file = None
    track = False

    def __init__(self):
        self.api = Api()
        #self.state = State()
        self.monitor = Monitor()
        Player.__init__(self)

    def set_last_file(self, filename):
        state.last_file = filename

    def get_last_file(self):
        return state.last_file

    def is_tracking(self):
        return state.track

    def disable_tracking(self):
        state.track = False

    def enable_tracking(self):
        state.track = True

    def reset_queue(self):
        if state.queued:
            self.api.reset_queue()
            state.queued = False

    def _check_video(self):
        self.monitor.waitForAbort(1)
        if not getCondVisibility('videoplayer.content(episodes)'):
            return
        state.track = True
        self.reset_queue()

    if callable(getattr(Player, 'onAVStarted', None)):
        def onAVStarted(self):  # pylint: disable=invalid-name
            """Will be called when Kodi has a video or audiostream"""
            self._check_video()
    else:
        def onPlayBackStarted(self):  # pylint: disable=invalid-name
            """Will be called when kodi starts playing a file"""
            self._check_video()

    def onPlayBackPaused(self):  # pylint: disable=invalid-name
        state.pause = True

    def onPlayBackResumed(self):  # pylint: disable=invalid-name
        state.pause = False

    def onPlayBackStopped(self):  # pylint: disable=invalid-name
        """Will be called when user stops playing a file"""
        self.reset_queue()
        self.api.reset_addon_data()
        state.reset()  # Reset state

    def onPlayBackEnded(self):  # pylint: disable=invalid-name
        """Will be called when Kodi has ended playing a file"""
        self.reset_queue()
        # Only reset state if not playing the next episode
        if not state.playing_next:
            self.api.reset_addon_data()
            state.reset()  # Reset state

    def onPlayBackError(self):  # pylint: disable=invalid-name
        """Will be called when when playback stops due to an error"""
        self.reset_queue()
        self.api.reset_addon_data()
        state.reset()  # Reset state
