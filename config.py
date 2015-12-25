import os

import jinja2


DEBUG = False

MAPS_API_KEY = 'AIzaSyBKqLZqJwhRMAOnyogfkFDetkA0iEXtDbk'

SEARCH_INDEX_NAME = 'places'
MAX_SEARCH_RESULTS = 1000

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        os.path.join(os.path.dirname(__file__), 'templates')),
    extensions=[
        'jinja2.ext.autoescape',
    ],
    autoescape=True)

# These are the types of places we display on the heat maps. The list
# of supported place types is defined at
# https://developers.google.com/places/supported_types#table1.
PLACE_TYPES = [
    'bar',
    'cafe',
    'restaurant',
]

SEARCH_RADIUS_METERS = 30000
