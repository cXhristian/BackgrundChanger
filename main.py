from subprocess import Popen, PIPE
import requests
from pyquery import PyQuery
import re
from random import choice
from os.path import abspath


class ScrapeException(Exception):
	pass


class Scrape:
	filters = {}

	def __init__(self):
		self.query = 'nature'

	def url(self):
		raise NotImplemented

	def load(self):
		if self.url and self.query:
			r = requests.get(self.url())
			if r.status_code == 200:
				return r.text
		raise ScrapeException('Failed to download')

	def filters_querystring(self):
		"""Turns a dict into a querystring"""
		return '&'.join([str(key) + '=' + str(value) for key, value in self.filters.items()])


class Wallbase(Scrape):

	def __init__(self):
		super().__init__()

	def url(self):
		if self.query:
			return 'http://wallbase.cc/search?q=' + self.query + self.filters_querystring()
		else:
			raise ScrapeException

	def parse(self):
		"""Parses html for thumbnails and returns full image url"""
		pq = PyQuery(self.load())
		thumbs = pq('section#thumbs > .thumbnail img')
		return 	[self.thumb2full(thumb) for thumb in thumbs]

	def thumb2full(self, pq):
		thumb_name = pq.attrib['data-original']
		groups = lambda n: re.match('http://thumbs\.wallbase\.cc//?(.+)/thumb-(\d+)\.jpg', thumb_name).group(n)
		return 'http://wallpapers.wallbase.cc/' + groups(1) + '/wallpaper-' + groups(2) + '.jpg'


class Background:

	def popen(self, command):
		p = Popen(command.split(), stdout=PIPE)
		return p.stdout.read()

	def get(self):
		return self.popen('gsettings get org.gnome.desktop.background picture-uri')

	def set(self, image):
		return self.popen('gsettings set org.gnome.desktop.background picture-uri ' + image)

	def random(self, service):
		# http://wallbase.cc/search?q=nature&order=random&thpp=1
		service.filter = {'order': 'random', 'thpp': 1}

		raise NotImplemented

	def save(self, background):
		with open('temp.jpg', 'bw+') as temp:
			temp.write(requests.get(background).content)


b = Background()
w = Wallbase()
w.query = 'nature'
backgrounds = w.parse()
background = choice(backgrounds)
b.save(background)
print(background)
b.set('file://' + abspath('temp.jpg'))
print(b.get())