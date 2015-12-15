import textwrap
import urllib2
import webapp2

import config


class AddCityHandler(webapp2.RequestHandler):

    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        self.response.write(textwrap.dedent("""\
            <!doctype html>
            <html>
              <body>
                <form method="post" action="">
                  <p>
                    <label for="longitude">Longitude:</label>
                    <input type="text" id="longitude" name="longitude">
                  </p>
                  <p>
                    <label for="latitude">Latitude:</label>
                    <input type="text" id="latitude" name="latitude">
                  </p>
                  <p>
                    <button type="submit">Add</button>
                  </p>
                </form>
              </body>
            </html>
        """))

    def post(self):
        lon = self.request.POST['longitude']
        lat = self.request.POST['latitude']
        location = '{0},{1}'.format(lon, lat)

        url = ('https://maps.googleapis.com/maps/api/place/radarsearch/'
               'json?key={key}&radius=10000&location={location}&'
               'type=restaurant').format(
                   key=config.PLACES_API_KEY,
                   location=location)
        res = urllib2.urlopen(url)

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write(res.geturl())
        self.response.write('\n')
        self.response.write(res.read())


handlers = webapp2.WSGIApplication([
    ('/admin/addcity', AddCityHandler),
], debug=config.DEBUG)
