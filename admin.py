import json
import logging
import math
import textwrap
import time
import urllib2
import webapp2

from google.appengine.ext import ndb
from google.appengine.api import search

import config
import models

R_EARTH = 6378137.0

def get_all_places(lat, lon, radius):
    logging.info('Fetching results for lat=%f, lon=%f', lat, lon)
    location = '{0},{1}'.format(lat, lon)
    url = ('https://maps.googleapis.com/maps/api/place/radarsearch/'
           'json?key={key}&radius={radius}&location={location}&'
           'type=restaurant').format(
               key=config.MAPS_API_KEY,
               radius=radius,
               location=location)
    res = json.load(urllib2.urlopen(url))
    logging.info('Num results from %s: %d', url, len(res['results']))

    places = []

    # If number of results >= 200, then that means we hit the Radar
    # Search's result limit, so we continue by dividing the geographic
    # search location into four smaller areas, and sending separate
    # requests for each area.
    if len(res['results']) >= 200:
        logging.info('Dividing request to four smaller ones.')

        dx = radius / 2.0 * math.cos(math.radians(45))
        dy = radius / 2.0 * math.sin(math.radians(45))

        for dir_x in (-1, 1):
            for dir_y in (-1, 1):
                new_lat = lat + dir_y * (dy / R_EARTH * 180 / math.pi)
                new_lon = lon + dir_x * (dx / R_EARTH * 180 / math.pi /
                                           math.cos(lat * math.pi / 180))

                time.sleep(1)  # Keep requests to a reasonable rate.
                places.extend(get_all_places(new_lat, new_lon, radius / 2.0))

    # If number of results < 200, we did not hit any limits, so there
    # is no need to divide the area into smaller areas.
    else:
        for place in res['results']:
            places.append(place)

    return places


class AddCityHandler(webapp2.RequestHandler):

    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        self.response.write(textwrap.dedent("""\
            <!doctype html>
            <html>
              <body>
                <form method="post" action="">
                  <p>
                    <label for="woeid">
                      <a href="https://en.wikipedia.org/wiki/GeoPlanet">WOEID</a>:
                    </label>
                    <input type="number" id="woeid" name="woeid">
                  </p>
                  <p>
                    <label for="name">Name:</label>
                    <input type="text" id="name" name="name">
                  </p>
                  <p>
                    <label for="latitude">Latitude:</label>
                    <input type="text" id="latitude" name="latitude">
                  </p>
                  <p>
                    <label for="longitude">Longitude:</label>
                    <input type="text" id="longitude" name="longitude">
                  </p>
                  <p>
                    <button type="submit">Add</button>
                  </p>
                </form>
              </body>
            </html>
        """))

    def post(self):
        woeid = self.request.POST['woeid']
        name = self.request.POST['name']
        lat = float(self.request.POST['latitude'])
        lon = float(self.request.POST['longitude'])

        city = models.City(
            id=woeid,
            name=name,
            location=ndb.GeoPt(lat=lat, lon=lon),
            ready=False)
        city.put()

        # TODO: This will not work in practice because App Engine
        # limits how long a request can take. Fix this by using Task
        # Queues for fetching places.
        places = get_all_places(lat, lon, 15000)

        index = search.Index(name=config.SEARCH_INDEX_NAME)
        for place in places:
            location = place['geometry']['location']
            doc = search.Document(
                doc_id=place['place_id'],
                fields=[
                    search.GeoField(name='location',
                                    value=search.GeoPoint(
                                        latitude=location['lat'],
                                        longitude=location['lng'])),
            ])
            index.put(doc)


handlers = webapp2.WSGIApplication([
    ('/admin/addcity', AddCityHandler),
], debug=config.DEBUG)
