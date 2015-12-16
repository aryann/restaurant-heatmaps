import json
import webapp2

from google.appengine.api import search

import config
import models


class MainPageHandler(webapp2.RequestHandler):

    def get(self):
        cities = []
        for city in models.City.get_ordered_cities().fetch():
            cities.append((
                city.name,
                'heatmap?lat={lat}&lon={lon}'.format(
                    lat=city.location.lat,
                    lon=city.location.lon)))

        template = config.JINJA_ENVIRONMENT.get_template('main.html')
        self.response.write(template.render({
            'cities': cities,
        }))


class HeatmapHandler(webapp2.RequestHandler):

    def get(self):
        # Grab the lat and lon query parameters if they both exist and
        # if they can both be parsed as floats.
        lat, lon = self.request.get('latitude'), self.request.get('longitude')
        try:
            lat = float(lat)
            lon = float(lon)
        except ValueError:
            lat, lon = None, None

        # We could get the latitude and longitude from the query
        # params, so fall back to default location.
        if not lat or not lon:
            lat, lon = config.DEFAULT_LAT_LON

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
            })
        else:
            debug = ''

        template = config.JINJA_ENVIRONMENT.get_template('heatmap.html')
        self.response.write(template.render({
            'debug': debug,
            'lat': lat,
            'lon': lon,
            'places': json.dumps(places, separators=(',', ':')),
            'maps_api_key': config.MAPS_API_KEY,
        }))


handlers = webapp2.WSGIApplication([
    ('/', MainPageHandler),
    ('/heatmap', HeatmapHandler),
], debug=config.DEBUG)
