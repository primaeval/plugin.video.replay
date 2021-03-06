# -*- coding: utf-8 -*-
import datetime, time
import xbmc
import xbmcaddon
import xbmcvfs
import sqlite3

from rpc import RPC
from xbmcswift2 import Plugin

plugin = Plugin()

def addon_id():
    return xbmcaddon.Addon().getAddonInfo('id')

def log(what):
    xbmc.log(repr(what))


class KodiPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)

    @classmethod
    def onPlayBackEnded(self):
        pass

    @classmethod
    def onPlayBackStopped(self):
        path = ""
        retry = 0
        while not path and retry < 50:
            path = xbmc.getInfoLabel('ListItem.FileNameAndPath')
            retry=retry+1
            time.sleep(0.1)
        label = xbmc.getInfoLabel('ListItem.Label')

        conn = sqlite3.connect(xbmc.translatePath('special://profile/addon_data/%s/replay.db' % addon_id()), detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()
        now = datetime.datetime.now() + datetime.timedelta(microseconds=1)  # add 1 microsecond, required for dbapi2
        if path:
            c.execute("INSERT OR REPLACE INTO links VALUES (?,?,?)", (label.decode("utf8"),path,now))
        conn.commit()
        conn.close()

    def onPlayBackStarted(self):
        try:
            file = self.getPlayingFile()
            response = RPC.player.get_item(playerid=1, properties=["title", "year", "thumbnail", "fanart", "showtitle", "season", "episode"])
        except:
            return
        item = response["item"]
        conn = sqlite3.connect(xbmc.translatePath('special://profile/addon_data/%s/replay.db' % addon_id()), detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()
        now = datetime.datetime.now() + datetime.timedelta(microseconds=1)  # add 1 microsecond, required for dbapi2
        if file:
            c.execute("INSERT OR REPLACE INTO streams VALUES (?,?,?)", (item["label"],file,now))
        conn.commit()
        conn.close()



conn = sqlite3.connect(xbmc.translatePath('special://profile/addon_data/%s/replay.db' % addon_id()), detect_types=sqlite3.PARSE_DECLTYPES)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS streams (title TEXT, file TEXT, date TIMESTAMP, PRIMARY KEY(file))')
c.execute('CREATE TABLE IF NOT EXISTS links (title TEXT, file TEXT, date TIMESTAMP, PRIMARY KEY(file))')
conn.commit()
conn.close()

player_monitor = KodiPlayer()

while not xbmc.abortRequested:
    xbmc.sleep(1000)

del player_monitor
