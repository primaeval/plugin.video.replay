
import xbmc
import sys
import urllib

title = xbmc.getInfoLabel('ListItem.Label')
path = xbmc.getInfoLabel('ListItem.FileNameAndPath')
icon = xbmc.getInfoLabel('ListItem.Icon ')
#title = "star wars"
url = "plugin://plugin.video.google.mkv/search_what_dialog/%s" % (urllib.quote_plus(title))
xbmc.log(url)
#xbmc.executebuiltin("ActivateMedia(videos,%s)" % url)
xbmc.executebuiltin("ActivateWindow(10025,%s,return)" % url)