# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from urllib.parse import quote
from urllib.request import urlopen
from utils import get_setting, log as ulog
import inspect
import json

class Api_Calls:
    api_key = get_setting('API')
    
    def log(self, msg, level=2):
        method = inspect.currentframe().f_back.f_code.co_name
        msg = f"[{method}] {msg}"
        ulog(msg, name=self.__class__.__name__, level=level)
        
    def tvmaze_get_imdb_id_from_series(self, series_name):
        url = "https://api.tvmaze.com/search/shows?q={}".format(
            quote(series_name)
        )
        
        self.log('URL for API Call for TVmaze: %s' % url, 2)

        try:
            data = json.loads(urlopen(url, timeout=10).read().decode("utf-8"))

            if not data:
                self.log('No Data found.', 2)
                return None

            # Erstes Suchergebnis
            show = data[0]["show"]

            # IMDb-ID direkt aus den externals
            imdb_id = show.get("externals", {}).get("imdb")

            if imdb_id:
                self.log('IMDB found: %s' % imdb_id, 2)
                return imdb_id

            return None

        except Exception as e:
            self.log('Error: %s ' % e, 2)
            return None

    def introdb_get_intro_data(self, imdb_id, season, episode):
        url = (
            "https://api.introdb.app/segments"
            "?imdb_id={}"
            "&season={}"
            "&episode={}"
            "&segment_type=intro"
        ).format(imdb_id, season, episode)
        
        self.log('URL for API Call for IntroDB: %s' % url, 2)
        
        try:
            response = urlopen(url, timeout=10)
            data = json.loads(response.read().decode("utf-8"))

            if not data:
                self.log('No Data found.', 2)
                return None

            # erstes Intro-Segment
            segment = data["intro"]
            if segment is None:
                return None
            else:
                return {
                    "intro_start": segment.get("start_sec"),
                    "intro_end": segment.get("end_sec"),
                    "updated_at": segment.get("updated_at")
                }

        except Exception as e:
            self.log('Error: %s ' % e, 2)
            return None
            
    def introdb_submit_intro(self, imdb_id, season, episode, intro_start, intro_end, segment_type="intro"):
        payload = {
            "imdb_id": imdb_id,
            "segment_type": segment_type,
            "season": int(season),
            "episode": int(episode),
            "start_sec": int(intro_start),
            "end_sec": int(intro_end)
        }

        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=15
            )

            self.log(
                f"IntroDB upload: {response.status_code} - {response.text}"
            )

            response.raise_for_status()

            try:
                return response.json()
            except Exception:
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response": response.text
                }

        except Exception as exc:
            self.log(f"IntroDB upload failed: {exc}")

            return {
                "success": False,
                "error": str(exc)
            }