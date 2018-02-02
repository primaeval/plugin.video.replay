from rpc import RPC
from xbmcswift2 import Plugin
import re
import requests
import xbmc,xbmcaddon,xbmcvfs,xbmcgui
import xbmcplugin
import base64
import random
#from HTMLParser import HTMLParser
import urllib
import sqlite3
import threading

import SimpleDownloader as downloader


plugin = Plugin()
big_list_view = False


def addon_id():
    return xbmcaddon.Addon().getAddonInfo('id')

def log(v):
    xbmc.log(repr(v),xbmc.LOGERROR)

#log(sys.argv)

def get_icon_path(icon_name):
    if plugin.get_setting('user.icons') == "true":
        user_icon = "special://profile/addon_data/%s/icons/%s.png" % (addon_id(),icon_name)
        if xbmcvfs.exists(user_icon):
            return user_icon
    return "special://home/addons/%s/resources/img/%s.png" % (addon_id(),icon_name)

def remove_formatting(label):
    label = re.sub(r"\[/?[BI]\]",'',label)
    label = re.sub(r"\[/?COLOR.*?\]",'',label)
    return label

def escape( str ):
    str = str.replace("&", "&amp;")
    str = str.replace("<", "&lt;")
    str = str.replace(">", "&gt;")
    str = str.replace("\"", "&quot;")
    return str

def unescape( str ):
    str = str.replace("&lt;","<")
    str = str.replace("&gt;",">")
    str = str.replace("&quot;","\"")
    str = str.replace("&amp;","&")
    return str


def download_m3u(title,url,header):
    headers = {}
    if header:
        heads = header.split("&") #TODO
        for h in heads:
            key,value = h.split("=")
            headers[key] = urllib.unquote_plus(value)
            headers[key] = value
    folder = plugin.get_setting('download')
    title = re.sub('[:\\/]','',title)
    file = folder+title+".ts"
    #log(file)
    data = requests.get(url,headers=headers).content
    lines = data.splitlines()
    chunks = [x for x in lines if x.startswith('http')]
    if not chunks:
        return
    f = xbmcvfs.File(file,"wb")
    d = xbmcgui.DialogProgressBG()
    d.create('Replay', 'Downloading %s' % title)
    done = 0
    total = len(chunks)
    for c in chunks:
        data = requests.get(c,headers=headers).content
        f.write(data)
        done = done + 1
        percent = 100.0 * done / total
        if plugin.get_setting('notify') == 'true':
            d.update(int(percent), message=title)
    f.close()
    d.close()

def download_file(title,url,header):
    headers = {}
    if header:
        heads = header.split("&") #TODO
        for h in heads:
            key,value = h.split("=")
            headers[key] = urllib.unquote_plus(value)
            
    folder = plugin.get_setting('download')
    title = re.sub('[:\\/]','',title)
    title = re.sub('\[.*?\]','',title)
    if not title:
        title = datetime.datetime.now()
    file = folder+title
    if not (file.endswith(".mkv") or file.endswith(".mp4") or file.endswith(".avi")):
        file = file+".ts"
    #log(file)
    total = int(requests.head(url, headers=headers).headers['Content-Length'])
    log(total)
    r = requests.get(url, stream=True, headers=headers)
    f = xbmcvfs.File(file,"wb")
    d = xbmcgui.DialogProgressBG()
    d.create('Replay', 'Downloading %s' % title)
    #done = 0
    #total = len(chunks)
    #d = xbmcgui.Dialog()
    size = 0
    for chunk in r.iter_content(chunk_size=1024):
        if chunk:
            f.write(chunk)
        else:
            break
        size = size + 1024
        if plugin.get_setting('notify') == 'true':
            #d.notification(title,str(total))
            #done = done + 1
            percent = 100.0 * size / total
            d.update(int(percent), message=title)
    f.close()
    d.close()

@plugin.route('/download/<name>/<url>')
def download(name,url):
    header = ""
    head_header = url.split('|',1)
    if len(head_header) == 2:
        url = head_header[0]
        header = head_header[1]
    cleanurl = re.sub('\?.*','',url)
    if cleanurl.endswith('m3u8'):
        threading.Thread(target=download_m3u,args=[name,url,header]).start()
    elif cleanurl.endswith('.mkv') or cleanurl.endswith('.mp4') or cleanurl.endswith('.avi'):
        threading.Thread(target=download_file,args=[name,url,header]).start()
    else:
        threading.Thread(target=download_file,args=[name,url,header]).start()
        '''
        downloads = plugin.get_storage('downloads')
        downloads[name] = url
        dl = downloader.SimpleDownloader()
        params = { "url": url, "download_path": plugin.get_setting('download') }
        dl.download(name, params)
        '''

@plugin.route('/stop_downloads')
def stop_downloads():
    downloads = plugin.get_storage('downloads')
    dl = downloader.SimpleDownloader()
    dl._stopCurrentDownload()
    #log(dl._getQueue())
    for name in downloads.keys():
        dl._removeItemFromQueue(name)
        del downloads[name]

@plugin.route('/start_downloads')
def start_downloads():
    dl = downloader.SimpleDownloader()
    dl._processQueue()

@plugin.route('/play/<url>')
def play(url):
    xbmc.executebuiltin('PlayMedia("%s")' % url)

@plugin.route('/execute/<url>')
def execute(url):
    xbmc.executebuiltin(url)

@plugin.route('/browse/<table>')
def browse(table):
    conn = sqlite3.connect(xbmc.translatePath('special://profile/addon_data/%s/replay.db' % addon_id()), detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS %s (title TEXT, file TEXT, date TIMESTAMP, PRIMARY KEY(date))' % table)
    items = []
    for row in c.execute('SELECT DISTINCT title,file FROM %s ORDER BY date DESC' % table):
        (title,file)   = row
        #log((title,year,file,link))
        if not title or (title == ".."):
            continue
        context_items = []
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Download', 'XBMC.RunPlugin(%s)' % (plugin.url_for(download, name=title.encode("utf8"), url=file))))
        title = re.sub('\[.*?\]','',title)
        if plugin.get_setting('url') == 'true':
            label = "%s [COLOR dimgray][%s][/COLOR]" % (title,file)
        else:
            label = title
        items.append(
        {
            'label': label,
            'path': file,#plugin.url_for('select', title=title,year=year),
            'thumbnail':get_icon_path('files'),
            'is_playable': True,
            'context_menu': context_items,
        })
    conn.commit()
    conn.close()
    return items

@plugin.route('/clear_database')
def clear_database():
    conn = sqlite3.connect(xbmc.translatePath('special://profile/addon_data/%s/replay.db' % addon_id()), detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('DROP TABLE streams')
    c.execute('DROP TABLE links')
    c.execute('CREATE TABLE IF NOT EXISTS streams (title TEXT, file TEXT, date TIMESTAMP, PRIMARY KEY(file))')
    c.execute('CREATE TABLE IF NOT EXISTS links (title TEXT, file TEXT, date TIMESTAMP, PRIMARY KEY(file))')
    conn.commit()
    conn.close()

@plugin.route('/')
def index():
    items = []
    items.append(
    {
        'label': "Streams",
        'path': plugin.url_for('browse', table='streams'),
        'thumbnail':get_icon_path('movies'),

    })
    items.append(
    {
        'label': "Links",
        'path': plugin.url_for('browse', table='links'),
        'thumbnail':get_icon_path('movies'),

    })
    items.append(
    {
        'label': "Clear Database",
        'path': plugin.url_for('clear_database'),
        'thumbnail':get_icon_path('movies'),

    })
    '''
    items.append(
    {
        'label': "Start Downloads",
        'path': plugin.url_for('start_downloads'),
        'thumbnail':get_icon_path('movies'),

    })
    items.append(
    {
        'label': "Stop Downloads",
        'path': plugin.url_for('stop_downloads'),
        'thumbnail':get_icon_path('movies'),

    })
    '''
    return items



if __name__ == '__main__':

    plugin.run()
    if big_list_view == True:
        view_mode = int(plugin.get_setting('view_mode'))
        plugin.set_view_mode(view_mode)
        plugin.set_content("files")