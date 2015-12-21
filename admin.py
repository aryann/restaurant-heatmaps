import json
import logging
import math
import textwrap
import time
import urllib2
import webapp2

from google.appengine.ext import ndb
from google.appengine.api import search
from google.appengine.api import taskqueue

import config
import models

R_EARTH = 6378137.0


class AddCityHandler(webapp2.RequestHandler):

    def get(self):
        template = config.JINJA_ENVIRONMENT.get_template('add_city.html')
        self.response.write(template.render({
            'debug': config.DEBUG,
        }))

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

        taskqueue.add(url='/admin/addcity/worker', params={
            'lat': lat,
            'lon': lon,
            'radius': 15000,
        })

        self.redirect('/')


class AddCityWorker(webapp2.RequestHandler):

    def post(self):
        lat = float(self.request.get('lat'))
        lon = float(self.request.get('lon'))
        radius = float(self.request.get('radius'))

        location = '{0},{1}'.format(lat, lon)
        url = ('https://maps.googleapis.com/maps/api/place/radarsearch/'
               'json?key={key}&radius={radius}&location={location}&'
               'type=restaurant').format(
                   key=config.MAPS_API_KEY,
                   radius=radius,
                   location=location)
        res = json.load(urllib2.urlopen(url))
        logging.info('Num results for lat=%f, lon=%f, radius=%f: %d',
                     lat, lon, radius, len(res['results']))

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

                    taskqueue.add(url='/admin/addcity/worker', params={
                        'lat': new_lat,
                        'lon': new_lon,
                        'radius': radius / 2.0,
                    })

        # If number of results < 200, we did not hit any limits, so there
        # is no need to divide the area into smaller areas.
        else:
            index = search.Index(name=config.SEARCH_INDEX_NAME)
            for place in res['results']:
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
    ('/admin/addcity/worker', AddCityWorker),
], debug=config.DEBUG)
