from google.appengine.ext import ndb


class City(ndb.Model):
    name = ndb.StringProperty(required=True)
    created = ndb.DateTimeProperty(auto_now_add=True)
    location = ndb.GeoPtProperty(required=True)

    @classmethod
    def get_ordered_cities(cls):
        return cls.query().order(cls.name)
