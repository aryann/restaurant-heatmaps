import os

import jinja2


DEFAULT_LAT_LON = (47.608013, -122.335167)  # Seattle, WA

DEBUG = True

PLACES_API_KEY = 'AIzaSyBKqLZqJwhRMAOnyogfkFDetkA0iEXtDbk'

SEARCH_INDEX_NAME = 'places'
MAX_SEARCH_RESULTS = 1000

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        os.path.join(os.path.dirname(__file__), 'templates')),
    extensions=[
        'jinja2.ext.autoescape',
    ],
    autoescape=True)
