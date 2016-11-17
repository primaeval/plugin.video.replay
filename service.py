# -*- coding: utf-8 -*-
import datetime
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
        pass

    def onPlayBackStarted(self):
        log("XXX")
        file = self.getPlayingFile()
        log(file)
        response = RPC.player.get_item(playerid=1, properties=["title", "year", "thumbnail", "fanart", "showtitle", "season", "episode"])
        log(response)
        item = response["item"]
        conn = sqlite3.connect(xbmc.translatePath('special://profile/addon_data/%s/replay.db' % addon_id()), detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO played VALUES (?,?,?)", (item["label"],file,datetime.datetime.now()))
        conn.commit()
        conn.close()

conn = sqlite3.connect(xbmc.translatePath('special://profile/addon_data/%s/replay.db' % addon_id()), detect_types=sqlite3.PARSE_DECLTYPES)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS played (title TEXT, file TEXT, date TIMESTAMP, PRIMARY KEY(file))')
conn.commit()
conn.close()

player_monitor = KodiPlayer()

while not xbmc.abortRequested:
    xbmc.sleep(1000)

del player_monitor
