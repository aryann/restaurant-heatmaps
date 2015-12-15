import os

import jinja2


DEBUG = True

PLACES_API_KEY = 'AIzaSyBKqLZqJwhRMAOnyogfkFDetkA0iEXtDbk'

SEARCH_INDEX_NAME = 'places'

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        os.path.join(os.path.dirname(__file__), 'templates')),
    extensions=[
        'jinja2.ext.autoescape',
    ],
    autoescape=True)
