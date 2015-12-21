import httplib
import json
import webapp2

from google.appengine.ext import ndb
from google.appengine.api import search

import config
import models


class MainPageHandler(webapp2.RequestHandler):

    def get(self):
        cities = []
        for city in models.City.get_ordered_cities().fetch():
            cities.append((
                city.name,
                'heatmap?city={0}'.format(city.key.urlsafe())))

        template = config.JINJA_ENVIRONMENT.get_template('main.html')
        self.response.write(template.render({
            'cities': cities,
        }))


class HeatmapHandler(webapp2.RequestHandler):

    def get(self):
        city = ndb.Key(urlsafe=self.request.GET['city']).get()
        lat, lon = city.location.lat, city.location.lon

        # Perform the search for the given location.
        index = search.Index(name=config.SEARCH_INDEX_NAME)

        places = []
        cursor = search.Cursor()

        while cursor:
            results = index.search(
                query=search.Query(
                    query_string=(
                        'distance(location, geopoint({lat}, {lon})) < 16000'.format(
                            lat=lat, lon=lon)),
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

        if config.DEBUG:
            debug = json.dumps({
                'num_found': results.number_found,
                'len_places': len(places),
            })
        else:
            debug = ''

        template = config.JINJA_ENVIRONMENT.get_template('heatmap.html')
        self.response.write(template.render({
            'name': city.name,
            'debug': debug,
            'lat': lat,
            'lon': lon,
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
