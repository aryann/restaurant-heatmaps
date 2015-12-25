from google.appengine.ext import ndb


class City(ndb.Model):
    name = ndb.StringProperty(required=True)
    created = ndb.DateTimeProperty(auto_now_add=True)
    location = ndb.GeoPtProperty(required=True)
    ready = ndb.BooleanProperty(required=True)

    @classmethod
    def get_ready_cities(cls):
        return cls.query(City.ready == True).order(cls.name)

    @classmethod
    def get_all_cities(cls):
        return cls.query().order(cls.name)


class CityAddRequest(ndb.Model):
    name = ndb.StringProperty(required=True)
    created = ndb.DateTimeProperty(auto_now_add=True)
