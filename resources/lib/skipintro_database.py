# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from datetime import datetime
from utils import log as ulog
import inspect
import os
import sqlite3
import xbmcaddon, xbmcvfs

class SkipIntro_Database:
    DB_NAME = "skipintro.db"

    def __init__(self):
        addon = xbmcaddon.Addon()

        addon_data_path = xbmcvfs.translatePath(
            addon.getAddonInfo("profile")
        )

        if not xbmcvfs.exists(addon_data_path):
            xbmcvfs.mkdirs(addon_data_path)

        self.db_path = os.path.join(addon_data_path, self.DB_NAME)

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        self._create_tables()
        
    def log(self, msg, level=2):
        method = inspect.currentframe().f_back.f_code.co_name
        msg = f"[{method}] {msg}"
        ulog(msg, name=self.__class__.__name__, level=level)

    def _create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tvshows (
                show_id INTEGER PRIMARY KEY,
                imdb_id TEXT,
                active INTEGER DEFAULT 1,
                use_show_data_only INTEGER DEFAULT 0,
                intro_start REAL,
                intro_end REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                episode_id INTEGER PRIMARY KEY,
                show_id INTEGER NOT NULL,
                intro_start REAL,
                intro_end REAL,
                active INTEGER DEFAULT 1,
                updated_at TEXT,
                FOREIGN KEY(show_id) REFERENCES tvshows(show_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodes_show_id
            ON episodes(show_id)
        """)

        self.conn.commit()

    # -------------------------------------------------
    # SHOWS
    # -------------------------------------------------

    def save_show(self, show_id, imdb_id=None, active=True, use_show_data_only=False, intro_start=None, intro_end=None):
        try:
            self.log('Trying to save tv show.', 2)
            cursor = self.conn.cursor()

            cursor.execute("""
                INSERT INTO tvshows (
                    show_id,
                    imdb_id,
                    active,
                    use_show_data_only,
                    intro_start,
                    intro_end
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(show_id) DO UPDATE SET
                    imdb_id = excluded.imdb_id,
                    active = excluded.active,
                    use_show_data_only = excluded.use_show_data_only,
                    intro_start = excluded.intro_start,
                    intro_end = excluded.intro_end
            """, (
                show_id,
                imdb_id,
                int(active),
                int(use_show_data_only),
                intro_start,
                intro_end
            ))

            self.conn.commit()
            self.log('Save tv show successfull.', 2)
        except Exception as e:
            self.log('Error: %s' % e, 2)

    def get_show(self, show_id):
        try:
            self.log('Trying to get show data.', 2)
            cursor = self.conn.cursor()

            cursor.execute("""
                SELECT *
                FROM tvshows
                WHERE show_id = ?
            """, (show_id,))

            row = cursor.fetchone()

            return dict(row) if row else None
        except Exception as e:
            self.log('Error: %s' % e, 2)

    def get_all_shows(self):
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT *
            FROM tvshows
            ORDER BY show_id
        """)

        return [dict(row) for row in cursor.fetchall()]

    def delete_show(self, show_id, delete_episodes=True):
        try:
            self.log('Trying to delete show.', 2)
            cursor = self.conn.cursor()

            if delete_episodes:
                cursor.execute("""
                    DELETE FROM episodes
                    WHERE show_id = ?
                """, (show_id,))

            cursor.execute("""
                DELETE FROM tvshows
                WHERE show_id = ?
            """, (show_id,))

            self.conn.commit()
            self.log('Delete show successfull.', 2)
        except Exception as e:
            self.log('Error: %s' % e, 2)

    # -------------------------------------------------
    # EPISODES
    # -------------------------------------------------

    def save_episode(self, show_id, episode_id, updated_at, intro_start=None, intro_end=None, active=True):
        try:
            self.log('Trying to save episode.', 2)
            cursor = self.conn.cursor()

            cursor.execute("""
                INSERT INTO episodes (
                    episode_id,
                    show_id,
                    intro_start,
                    intro_end,
                    active,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(episode_id) DO UPDATE SET
                    show_id = excluded.show_id,
                    intro_start = excluded.intro_start,
                    intro_end = excluded.intro_end,
                    active = excluded.active,
                    updated_at = excluded.updated_at
            """, (
                episode_id,
                show_id,
                intro_start,
                intro_end,
                int(active),
                updated_at
            ))

            self.conn.commit()
            self.log('Save episode successfull.', 2)
        except Exception as e:
            self.log('Error: %s' % e, 2)

    def get_episode(self, episode_id):
        try:
            self.log('Trying to get episode data.', 2)
            cursor = self.conn.cursor()

            cursor.execute("""
                SELECT *
                FROM episodes
                WHERE episode_id = ?
            """, (episode_id,))

            row = cursor.fetchone()

            return dict(row) if row else None
        except Exception as e:
            self.log('Error: %s' % e, 2)

    def get_episodes_by_show(self, show_id):
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT *
            FROM episodes
            WHERE show_id = ?
            ORDER BY episode_id
        """, (show_id,))

        return [dict(row) for row in cursor.fetchall()]

    def delete_episode(self, episode_id):
        try:
            self.log('Trying to delete episode.', 2)
            cursor = self.conn.cursor()

            cursor.execute("""
                DELETE FROM episodes
                WHERE episode_id = ?
            """, (episode_id,))

            self.conn.commit()
            self.log('Delete episode successfull.', 2)
        except Exception as e:
            self.log('Error: %s' % e, 2)

    # -------------------------------------------------
    # CONNECTION
    # -------------------------------------------------

    def close(self):
        if self.conn:
            self.conn.close()