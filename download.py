
import xbmc
import sys
import urllib

title = xbmc.getInfoLabel('ListItem.Label')
path = xbmc.getInfoLabel('ListItem.FileNameAndPath')
icon = xbmc.getInfoLabel('ListItem.Icon ')
#title = "star wars"
url = "plugin://plugin.video.google.mkv/download/%s/%s" % (urllib.quote_plus(title),urllib.quote_plus(path))
xbmc.log(url)
xbmc.executebuiltin("PlayMedia(%s)" % url)
#xbmc.executebuiltin("ActivateWindow(10025,%s,return)" % url)