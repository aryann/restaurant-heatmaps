import json
import logging
import math
import textwrap
import time
import urlparse
import webapp2

from google.appengine.ext import ndb
from google.appengine.api import search
from google.appengine.api import taskqueue
from google.appengine.api import urlfetch

import config
import models

R_EARTH = 6378137.0

class ListCitiesHandler(webapp2.RequestHandler):

    def get(self):
        cities = []
        for city in models.City.get_ordered_cities().fetch():
            cities.append((
                city.name,
                'modifycity?city={0}'.format(city.key.urlsafe())))
        template = config.JINJA_ENVIRONMENT.get_template('list_cities.html')
        self.response.write(template.render({
            'cities': cities,
        }))


class ModifyCityHandler(webapp2.RequestHandler):

    def get(self):
        city_query_param = self.request.get('city')

        if city_query_param:
            city_key = ndb.Key(urlsafe=city_query_param)
            city = city_key.get()
            context = {
                'woeid': city.key.id(),
                'name': city.name,
                'lat': city.location.lat,
                'lon': city.location.lon,
                'ready': city.ready,
            }
        elif config.DEBUG:
            context = {
                'woeid': 2490383,
                'name': 'Seattle, WA, USA',
                'lat': 47.608013,
                'lon': -122.335167,
                'ready': False,
            }
        else:
            context = {}

        template = config.JINJA_ENVIRONMENT.get_template('modify_city.html')
        self.response.write(template.render(context))

    def post(self):
        woeid = self.request.POST['woeid']
        name = self.request.POST['name']
        lat = float(self.request.POST['latitude'])
        lon = float(self.request.POST['longitude'])

        city = models.City(
            id=woeid,
            name=name,
            location=ndb.GeoPt(lat=lat, lon=lon),
            ready=bool(self.request.get('ready')))
        city.put()

        if self.request.get('getdata'):
            taskqueue.add(url='/admin/modifycity/worker', params={
                'lat': lat,
                'lon': lon,
                'radius': config.SEARCH_RADIUS_METERS,
            }, queue_name='fetch-places')

        self.redirect('/admin/')


class ModifyCityWorker(webapp2.RequestHandler):

    def post(self):
        lat = float(self.request.get('lat'))
        lon = float(self.request.get('lon'))
        radius = float(self.request.get('radius'))

        location = '{0},{1}'.format(lat, lon)
        url = ('https://maps.googleapis.com/maps/api/place/radarsearch/'
               'json?key={key}&radius={radius}&location={location}&'
               'type={types}').format(
                   key=config.MAPS_API_KEY,
                   radius=radius,
                   location=location,
                   types='|'.join(config.PLACE_TYPES))
        logging.info('Requesting URL: %s', url)
        res = json.loads(urlfetch.fetch(url).content)
        logging.info('Num results for lat=%f, lon=%f, radius=%f: %d',
                     lat, lon, radius, len(res['results']))

        # If number of results >= 190, then that means we hit the Radar
        # Search's result limit, so we continue by dividing the geographic
        # search location into four smaller areas, and sending separate
        # requests for each area.
        #
        # Note that the API advertises a page size limit of 200. In
        # practice, however, sometimes a page can have <200 results
        # AND there are more pages of results. This is a bug, and to
        # be safe, we use 190 as the cut off.
        if len(res['results']) >= 190:
            logging.info('Dividing request into four smaller ones.')

            radius_axis_projection = radius / (2.0 * math.sqrt(2))
            d_lat = radius_axis_projection / R_EARTH * 180 / math.pi
            d_lon = d_lat / math.cos(lat * math.pi / 180)

            for dir_x in (-1, 1):
                for dir_y in (-1, 1):
                    new_lat = lat + dir_y * d_lat
                    new_lon = lon + dir_x * d_lon

                    taskqueue.add(url='/admin/modifycity/worker', params={
                        'lat': new_lat,
                        'lon': new_lon,
                        'radius': radius / 2.0,
                    }, queue_name='fetch-places')

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


class RefreshAllCitiesHandler(webapp2.RequestHandler):

    def post(self):
        for city in models.City.get_ordered_cities().fetch():
            taskqueue.add(url='/admin/modifycity/worker', params={
                'lat': city.location.lat,
                'lon': city.location.lon,
                'radius': config.SEARCH_RADIUS_METERS,
            }, queue_name='fetch-places')
        self.redirect('/admin/')


class PopulateMemcacheHandler(webapp2.RequestHandler):

    def get(self):
        for city in models.City.get_ordered_cities().fetch():
            taskqueue.add(url='/admin/populatememcache/worker', params={
                'city': city.key.urlsafe(),
            }, queue_name='populate-memcache')


class PopulateMemcacheWorker(webapp2.RequestHandler):

    def post(self):
        original = urlparse.urlparse(self.request.url)
        city_url = urlparse.urlunparse(
            (original.scheme, original.netloc, '/heatmap',
             '', 'city={0}'.format(self.request.get('city')), ''))
        urlfetch.fetch(city_url)


handlers = webapp2.WSGIApplication([
    ('/admin/', ListCitiesHandler),
    ('/admin/modifycity', ModifyCityHandler),
    ('/admin/modifycity/worker', ModifyCityWorker),
    ('/admin/refreshallcities', RefreshAllCitiesHandler),
    ('/admin/populatememcache', PopulateMemcacheHandler),
    ('/admin/populatememcache/worker', PopulateMemcacheWorker),
], debug=config.DEBUG)
