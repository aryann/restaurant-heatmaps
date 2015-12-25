import collections
import httplib
import json
import webapp2

from google.appengine.api import memcache
from google.appengine.api import search
from google.appengine.ext import ndb

import config
import models


class MainPageHandler(webapp2.RequestHandler):

    def get(self):
        cities = []
        for city in models.City.get_ready_cities().fetch():
            cities.append((
                city.name,
                'heatmap?city={0}'.format(city.key.urlsafe())))

        template = config.JINJA_ENVIRONMENT.get_template('main.html')
        self.response.write(template.render({
            'cities': cities,
        }))


CacheEntry = collections.namedtuple(
    'CacheEntry', ['city', 'places'])

def serialize_places_for_memcache(places):
    return ';'.join('{0},{1}'.format(lat, lon) for lat, lon in places)


def deserialize_places_from_memcache(places):
    return [tuple(float(val) for val in place.split(','))
            for place in places.split(';')]


class HeatmapHandler(webapp2.RequestHandler):

    def get(self):
        city_key = ndb.Key(urlsafe=self.request.GET['city'])
        cache_entry = memcache.get(city_key.id())

        if cache_entry:
            city = cache_entry.city

            # It's better to perform custom serialization than to
            # rely on Python pickling because Memcache has a limit of
            # 1 MB per entry.
            places = deserialize_places_from_memcache(cache_entry.places)

        else:
            city = city_key.get()

            # Perform the search for the given location.
            index = search.Index(name=config.SEARCH_INDEX_NAME)

            places = []
            cursor = search.Cursor()

            while cursor:
                results = index.search(
                    query=search.Query(
                        query_string=(
                            'distance(location, geopoint({lat}, {lon})) < {search_radius}'.format(
                                lat=city.location.lat,
                                lon=city.location.lon,
                                search_radius=config.SEARCH_RADIUS_METERS)),
                        options=search.QueryOptions(
                            cursor=cursor,
                            returned_fields=[
                                'location',
                            ],
                            limit=config.MAX_SEARCH_RESULTS)))
                cursor = results.cursor

                # Convert the search results to a JSON-serializable list that
                # can be passed on to the JavaScript code in the template.
                for res in results:
                    value = res.fields[0].value
                    places.append((value.latitude, value.longitude))

            memcache.add(
                city_key.id(),
                value=CacheEntry(
                    city=city,
                    places=serialize_places_for_memcache(places)))

        template = config.JINJA_ENVIRONMENT.get_template('heatmap.html')
        self.response.write(template.render({
            'name': city.name,
            'lat': city.location.lat,
            'lon':  city.location.lon,
            'places': json.dumps(places, separators=(',', ':')),
            'maps_api_key': config.MAPS_API_KEY,
        }))


class NewCityRequestHandler(webapp2.RequestHandler):

    def post(self):
        name = self.request.POST['name']
        if not name:
            self.response.write("I'm going to need a non-empty name.\n")
            self.response.set_status(httplib.BAD_REQUEST)
            return

        models.CityAddRequest(name=name).put()
        self.response.write("Thanks! We're on it.\n")


handlers = webapp2.WSGIApplication([
    ('/', MainPageHandler),
    ('/heatmap', HeatmapHandler),
    ('/newcityrequest', NewCityRequestHandler),
], debug=config.DEBUG)
