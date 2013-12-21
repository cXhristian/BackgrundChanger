#!/usr/bin/env python3
from os.path import abspath
from pyquery import PyQuery
from random import choice
from subprocess import Popen, PIPE
import json
import re
import requests
import time


class ScrapeException(Exception):
	pass


class Scrape:
	filters = {}

	def __init__(self, background):
		self.background = background()
		self.filters = {}
		self.base_url = None

	def url(self):
		"""Simple method for creating a url based on base url and querystrings"""
		if self.filters:
			return self.base_url + self.filters_querystring()
		else:
			raise ScrapeException('No fiters set')

	def load(self):
		"""Downloads html from self.url"""
		if DEBUG:
			print(self.url())
		r = requests.get(self.url())
		if r.status_code == 200:
			return r.text
		raise ScrapeException('Failed to download')

	def parse(self):
		"""Parses html for thumbnails and returns full image urls"""
		self.pq = PyQuery(self.load())

	def json_parse(self):
		self.json = json.loads(self.load())

	def filters_querystring(self):
		"""Turns a dict into a querystring"""
		return '?' + '&'.join([str(key) + '=' + str(value) for key, value in self.filters.items()])


class Wallbase(Scrape):

	def __init__(self, background):
		super().__init__(background)
		self.base_url = 'http://wallbase.cc/search'

	def parse(self):
		super().parse()
		thumbs = self.pq('section#thumbs > .thumbnail img')
		return 	[self.thumb2full(thumb) for thumb in thumbs]

	def thumb2full(self, thumb):
		"""Converts thumbnail url into full image url"""
		thumb_name = thumb.attrib['data-original']
		groups = lambda n: re.match('http://thumbs\.wallbase\.cc//?(.+)/thumb-(\d+)\.jpg', thumb_name).group(n)
		return 'http://wallpapers.wallbase.cc/' + groups(1) + '/wallpaper-' + groups(2) + '.jpg'

	def random_search(self, query):
		"""Searches with random ordering"""
		if query:
			self.filters = {'order': 'random', 'thpp': 1, 'q': query}
		self.background.set_background(self.parse())

	def search(self, query):
		"""Searches with default sorting and takes a random background from the first 20 results"""
		self.filters['q'] = query
		self.background.set_background(self.parse())


class Google(Scrape):

	def __init__(self, background):
		super().__init__(background)
		self.base_url = 'https://www.google.com/search'

	def parse(self):
		super().parse()
		thumbs = self.pq('table.images_table td')
		return [self.thumb2full(thumb) for thumb in thumbs]

	def thumb2full(self, thumb):
		google_url = thumb.find('a').attrib['href']
		try:
			return re.search(r'imgurl=(.+)&imgrefurl', google_url).group(1)
		except AttributeError:
			pass

	def search(self, query):
		"""Searches with default sorting and takes a random background from the first 20 results"""
		self.filters = {'tbm': 'isch', 'tbs': 'isz:l', 'q': query, 'sout': 1}
		self.background.set_background(self.parse())


class Reddit(Scrape):
	
	def __init__(self, background):
		super().__init__(background)
		self.base_url = 'http://reddit.com/'

	def parse(self):
		super().json_parse()
		posts = self.json['data']['children']
		image_posts = [post for post in posts if post['is_self'] == False]
		for post in posts:
			print(post['is_self'])

	def search(self, query):
		self.filters = {'is_self': True}
		self.background.set_background(self.parse())

class Background:

	def popen(self, command):
		p = Popen(command.split(), stdout=PIPE)
		return p.stdout.read()

	def get(self):
		raise NotImplementedError

	def set(self, image):
		raise NotImplementedError

	def set_background(self, backgrounds):
		"""Takes several backgrounds, selects a random and saves it"""
		if not backgrounds:
			print('No background found')
		else:
			background = choice(backgrounds)
			self.save(background)

	def save(self, background):
		"""Saves background and sets it as wallpaper"""
		if DEBUG:
			print(background)
		filename = abspath('temp.jpg')
		with open(filename, 'bw+') as temp:
			temp.write(requests.get(background).content)
		self.set(filename)
		if DEBUG:
			print(self.get())
		return filename


class GnomeBackground(Background):

	def versiontuple(self, v):
		return tuple(map(int, (v.split("."))))

	def version(self):
		version = self.popen('gnome-session --version').decode("utf-8")
		try:
			return self.versiontuple(re.match(r'gnome-session ([\d\.]+)', version).group(1))
		except (ValueError, AttributeError)	:
			return (0, 0)

	def get(self):
		return self.popen('gsettings get org.gnome.desktop.background picture-uri')

	def set(self, image):
		# Gnome 3.10 doesn't update background if using the same uri
		print(self.version())
		if self.version() > (3,8):
			self.popen('gsettings set org.gnome.desktop.background picture-uri ""')
			# Also won't update if changing too fast
			time.sleep(1)
		return self.popen('gsettings set org.gnome.desktop.background picture-uri file://' + image)

DEBUG = True

def main():
	w = Wallbase(GnomeBackground)
	w.search('space')
	# w.random_search('space')


if __name__ == '__main__':
	main()
