import webapp2

import config


class MainPageHandler(webapp2.RequestHandler):

    def get(self):
        template = config.JINJA_ENVIRONMENT.get_template('main.html')
        self.response.write(template.render({}))


handlers = webapp2.WSGIApplication([
    ('/', MainPageHandler),
], debug=config.DEBUG)
