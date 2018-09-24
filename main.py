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
import json
import os,os.path
import subprocess
import stat
import datetime
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

def windows():
    if os.name == 'nt':
        return True
    else:
        return False


def android_get_current_appid():
    with open("/proc/%d/cmdline" % os.getpid()) as fp:
        return fp.read().rstrip("\0")


@plugin.route('/delete_ffmpeg')
def delete_ffmpeg():
    if xbmc.getCondVisibility('system.platform.android'):
        ffmpeg_dst = '/data/data/%s/ffmpeg' % android_get_current_appid()
        xbmcvfs.delete(ffmpeg_dst)


def ffmpeg_location():
    ffmpeg_src = xbmc.translatePath(plugin.get_setting('ffmpeg'))

    if xbmc.getCondVisibility('system.platform.android'):
        ffmpeg_dst = '/data/data/%s/ffmpeg' % android_get_current_appid()

        if (plugin.get_setting('ffmpeg') != plugin.get_setting('ffmpeg.last')) or (not xbmcvfs.exists(ffmpeg_dst) and ffmpeg_src != ffmpeg_dst):
            xbmcvfs.copy(ffmpeg_src, ffmpeg_dst)
            plugin.set_setting('ffmpeg.last',plugin.get_setting('ffmpeg'))

        ffmpeg = ffmpeg_dst
    else:
        ffmpeg = ffmpeg_src

    if ffmpeg:
        try:
            st = os.stat(ffmpeg)
            if not (st.st_mode & stat.S_IXUSR):
                try:
                    os.chmod(ffmpeg, st.st_mode | stat.S_IXUSR)
                except:
                    pass
        except:
            pass
    if xbmcvfs.exists(ffmpeg):
        return ffmpeg
    else:
        xbmcgui.Dialog().notification("Replay", "ffmpeg exe not found!")

@plugin.route('/record_last')
def record_last():
    conn = sqlite3.connect(xbmc.translatePath('special://profile/addon_data/%s/replay.db' % addon_id()), detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS streams (title TEXT, file TEXT, date TIMESTAMP, PRIMARY KEY(date))')
    items = []
    row = c.execute('SELECT DISTINCT title,file FROM streams ORDER BY date DESC').fetchone()
    (title,file)   = row
    #log((title,file))
    threading.Thread(target=record,args=[title,file]).start()

def sane_name(name):
    quote = {'"': '%22', '|': '%7C', '*': '%2A', '/': '%2F', '<': '%3C', ':': '%3A', '\\': '%5C', '?': '%3F', '>': '%3E'}
    for char in quote:
        name = name.replace(char, quote[char])
    return name

@plugin.route('/record/<name>/<url>')
def record(name,url):
    #log((name,url))

    url_headers = url.split('|', 1)
    url = url_headers[0]
    headers = {}
    if len(url_headers) == 2:
        sheaders = url_headers[1]
        aheaders = sheaders.split('&')
        if aheaders:
            for h in aheaders:
                k, v = h.split('=', 1)
                headers[k] = urllib.unquote_plus(v)

    kodi_recordings = xbmc.translatePath(plugin.get_setting('recordings'))

    path = os.path.join(kodi_recordings, sane_name(name) + ' ' + datetime.datetime.now().strftime("%Y-%m-%d %H-%M") +'.ts')
    if len(path) >= 260:
        path = os.path.join(kodi_recordings,  datetime.datetime.now().strftime("%Y-%m-%d %H-%M") +'.ts')

    cmd = [ffmpeg_location()]
    for h in headers:
        cmd.append("-headers")
        cmd.append("%s:%s" % (h, headers[h]))
    cmd.append("-i")
    cmd.append(url)
    cmd = cmd + ["-reconnect", "1", "-reconnect_at_eof", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "300", "-y", "-t", str(3600*6), "-c", "copy",'-f', 'mpegts','-']
    #log(cmd)
    #log(path)

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=windows())

    video = xbmcvfs.File(path,'wb')
    while True:
      data = p.stdout.read(1000000)
      video.write(data)
    video.close()


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
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Record', 'XBMC.RunPlugin(%s)' % (plugin.url_for(record, name=title.encode("utf8"), url=file))))
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
        'label': "Recordings Folder",
        'path': plugin.get_setting('recordings'),
        'thumbnail':get_icon_path('recordings'),
    })
    items.append(
    {
        'label': "Download Folder",
        'path': plugin.get_setting('download'),
        'thumbnail':get_icon_path('recordings'),
    })
    items.append(
    {
        'label': "Clear Database",
        'path': plugin.url_for('clear_database'),
        'thumbnail':get_icon_path('movies'),

    })
    items.append(
    {
        'label': "Record Last Played",
        'path': plugin.url_for('record_last'),
        'thumbnail':get_icon_path('recordings'),

    })
    items.append(
    {
        'label': "Delete ffmpeg",
        'path': plugin.url_for('delete_ffmpeg'),
        'thumbnail':get_icon_path('settings'),
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