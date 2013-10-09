#!/usr/bin/python2

# -*- coding: utf-8 -*-

import sqlite3 as db
import sys
import os
import pycurl
import StringIO
import re
import urllib
import json
from random import shuffle

PROFILE = 'default'

argc = len(sys.argv)
if argc < 3 or argc > 4:
    sys.stderr.write('Usage: %s /path/to/dir count_of_songs [PROFILE]\n'%sys.argv[0])
    sys.exit(1)
PATH_TO_SAVE=sys.argv[1]
count_of_songs = int(sys.argv[2])
if argc==4:
	print "update PROFILE"
	PROFILE=sys.argv[3]

#sys.exit(0)

# find needed profile dir and cookiesdb from it
cookiedbpath = os.environ['HOME']+'/.mozilla/firefox/'
for name in os.listdir(cookiedbpath):
	if os.path.isdir(cookiedbpath+name) and (PROFILE in name):
		cookiedbpath=cookiedbpath+name+'/cookies.sqlite'
		break

what = '.vk.com'
addHash='undef'
connection = db.connect(cookiedbpath)
cursor = connection.cursor()
contents = "name, value"

cursor.execute("SELECT " +contents+ " FROM moz_cookies WHERE host='" +what+ "'")
cookiemas=[]
for row in cursor.fetchall():
	cookiemas.append(row[0]+'='+row[1])
connection.close()

cookiestr='; '.join(cookiemas)

tmpdir = '/tmp/add_audio_vk'
songlist=[]
# this is first run, so lets write hash value
if not os.path.isdir(tmpdir):
	mus = pycurl.Curl()
	ans = StringIO.StringIO()
	# let's figure out our pageid
	mus.setopt(pycurl.HTTPHEADER, [str('Cookie: '+cookiestr)])
	mus.setopt(pycurl.URL, 'https://vk.com/feed')
	mus.setopt(pycurl.FOLLOWLOCATION, 1)
	mus.setopt(pycurl.WRITEFUNCTION, ans.write)
	mus.setopt(pycurl.USERAGENT, "Mozilla/5.0 (X11; Linux x86_64; rv:20.0) Gecko/20100101 Firefox/20.0")

	mus.perform()
	mus.close()
	
	data=ans.getvalue()
	profile=re.search('<a href=\"/([^\"]+)\" onclick=\"return nav.go\(this, event, {noback: true}\)\" id=\"myprofile\" class=\"left_row\">',data)
	pageid=profile.group(1)
	
	# figure out our hash
	mus = pycurl.Curl()
	ans = StringIO.StringIO()
	mus.setopt(pycurl.HTTPHEADER, [str('Cookie: '+cookiestr)])
	mus.setopt(pycurl.URL, 'https://vk.com/'+pageid)
	mus.setopt(pycurl.FOLLOWLOCATION, 1)
	mus.setopt(pycurl.VERBOSE, 0)
	mus.setopt(pycurl.WRITEFUNCTION, ans.write)
	mus.setopt(pycurl.USERAGENT, "Mozilla/5.0 (X11; Linux x86_64; rv:20.0) Gecko/20100101 Firefox/20.0")

	mus.perform()
	mus.close()
	
	data=ans.getvalue()
	addhash=re.search('Page.audioStatusUpdate\(\'([^\']+)\'\)',data).group(1)
	
	os.mkdir(tmpdir)
	fwrite=open(tmpdir+'/addhash','w')
	fwrite.write(addhash)
	fwrite.close()

fread=open(tmpdir+'/addhash','r')
HASHSUM=fread.read()
fread.close()

# looking for first match
mus = pycurl.Curl()
ans = StringIO.StringIO()
mus.setopt(pycurl.URL, 'https://m.vk.com/audio')
mus.setopt(pycurl.HTTPHEADER, [str('Cookie: '+cookiestr),'X-Requested-With: XMLHttpRequest'])
mus.setopt(pycurl.POST, 0)
mus.setopt(pycurl.VERBOSE, 0)
mus.setopt(pycurl.FOLLOWLOCATION, 1)
mus.setopt(pycurl.WRITEFUNCTION, ans.write)
mus.perform()

mus.close()

data=ans.getvalue()
js = json.loads(data)

if js[1]==False and js[4]==False:
    sys.stderr.write('Firefox\'s profile is unauthorized at vk.com\n')
    sys.exit(1)
page = js[5]

page1=page
page1 = re.sub(r'cur.au_search = new QuickSearch\(extend\(',r'',page1)
page1 = re.sub(r'\)\);extend\(cur,{module:\'audio\'}\);',r'',page1)
page1 = re.sub(r'\\/',r'/',page1)
page1 = re.sub(r'mp3\?([^"]+)',r'mp3',page1)
page1 = re.sub("(\n|\r).*", '', page1)
page1 = re.sub(',"_new":true\}, \{*','}',page1)

mlist = json.loads(page1)
count=0
for index, mas in mlist['_cache'].iteritems():
	#mas[2] - link
	#mas[3] - author
	#mas[4] - song
	songlist.append(dict([('link',mas[2]),('author',mas[3]),('song',mas[4])]))
	count=count+1
##
offset=count
if count==200:
	while (count>0):
		count=0
		mus = pycurl.Curl()
		ans = StringIO.StringIO()
		mus.setopt(pycurl.URL, 'https://m.vk.com/audio')
		mus.setopt(pycurl.HTTPHEADER, [str('Cookie: '+cookiestr),'X-Requested-With: XMLHttpRequest'])
		req = '_ajax=1&offset=%d'%(offset)
		mus.setopt(pycurl.POSTFIELDS, req)
		mus.setopt(pycurl.POST, 1)
		mus.setopt(pycurl.VERBOSE, 0)
		mus.setopt(pycurl.FOLLOWLOCATION, 1)
		mus.setopt(pycurl.WRITEFUNCTION, ans.write)
		mus.perform()
		mus.close()
		data=ans.getvalue()
		data = re.sub(r'\\/',r'/',data)
		data = re.sub(r'mp3\?([^"]+)',r'mp3',data)
		mlist = json.loads(data)
		mlist=mlist[3][0]
		if len(mlist)>0:
			for index, mas in mlist.iteritems():
				songlist.append(dict([('link',mas[2]),('author',mas[3]),('song',mas[4])]))
				count=count+1
		offset=offset+count

print "total count: %d"%(len(songlist))

shuffle(songlist)

mkremove = "if [ -e '%(path)s' ]; then rm -r '%(path)s'; fi; mkdir '%(path)s'" % {"path":PATH_TO_SAVE}
os.system(mkremove)

for i in range(count_of_songs):
	print "%s - %s" %(songlist[i]['author'],songlist[i]['song'])
	os.system("wget -P '%s' %s"%(PATH_TO_SAVE,songlist[i]['link']))

print "complete"
sys.exit(0)
