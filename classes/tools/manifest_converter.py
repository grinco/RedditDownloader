import gzip
import json
from classes.util.settings import Settings
from classes.util import stringutil
from classes.util import manifest
from classes.reddit import reddit as rd

_verbose = False
_converted = 0  # For testing.

def load(file):
	with gzip.GzipFile(file, 'rb') as data_file:
		data = json.loads(data_file.read().decode('utf8'))
	return data


def find_comment(e):
	""" Legacy RedditElement Comments incorrectly grabbed the ID of their parent as their own. """
	if len(e['urls']) == 0:
		return None
	for c in rd.get_submission_comments(e['id']):
		try:
			c_urls = stringutil.html_elements(c.body_html, 'a', 'href')
		except AttributeError:
			continue
		if len(c_urls) == 0:
			continue
		if all(u in c_urls for u in e['urls']):
			return c.name


def convert(save_base, data):
	global _converted
	elems = data['elements']
	base = stringutil.normalize_file(save_base + '/')
	broken = 0
	total = len(elems['failed'] + elems['completed'])
	i = 0
	for e in elems['failed'] + elems['completed']:
		if not _verbose:
			print('Converting: %s (%s%%)' % (e['id'], round(i/total * 100, 2)), end='\r')
			i += 1
		e['parent'] = None
		body = ''
		if e['type'] == 'Comment':
			e['parent'] = e['id']  # Previous versions used Parent ID instead of their own.
			if _verbose:
				print('Conversion needed: [%s]' % e['id'])
			nid = find_comment(e)
			if not nid:
				broken += 1
				print('Could not match comment. Cannot migrate over. [%s]' % e['id'])
				continue
			else:
				if _verbose:
					print('Matched! %s' % nid)
				e['id'] = nid

		for k, v in e['files'].items():
			if v:
				e['files'][k] = stringutil.normalize_file(v).replace(base, '').lstrip('/\\')
		if _verbose:
			print(e)
		manifest.direct_insert_post(e['id'], e['author'], e['source_alias'], e['subreddit'], e['title'], e['type'], e['files'], e['parent'], body)
		_converted += 1
	print('Comments that cannot be converted: %s' % broken)


if __name__ == '__main__':
	#  All of this is just to stage everything as if it were running live.
	_verbose = True
	import os
	sf = input('Enter the exact path to your settings file: ')
	_set = Settings(sf, can_save=False)
	os.chdir(os.path.dirname(sf))
	os.chdir(_set.save_base())
	auth_info = _set.get('auth')
	manifest.create('manifest.sqldb')
	rd.init(client_id=auth_info['client_id'], client_secret=auth_info['client_secret'],
				password=auth_info['password'], user_agent=auth_info['user_agent'], username=auth_info['username'])
	rd.login()
	_data = load(input('Enter the exact path to the old Manifest file: '))
	print(_data)
	convert(_set.save_base(), _data)
	# TODO: Replicate this in a Test, to make sure it's always working.