# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from tailbone import DEBUG, PREFIX, AppError

import logging
import math
import random
import webapp2

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel

def HaversineDistance(location1, location2):
  """Method to calculate Distance between two sets of Lat/Lon."""
  lat1, lon1 = location1
  lat2, lon2 = location2
  #Calculate Distance based in Haversine Formula
  dlat = math.radians(lat2-lat1)
  dlon = math.radians(lon2-lon1)
  a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
  c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
  # c * 6371  # Earth's radius in km
  return c


# These are just random guesses based on the name I have no idea where they actually are.
LOCATIONS = {
  (36.0156, 114.7378): ["us-central1-a", "us-central1-b", "us-central2-a"],
  (52.5233, 13.4127): ["europe-west1-a", "europe-west1-b"],
}


# Prefixing internal models with Tailbone to avoid clobbering when using RESTful API
class TailboneCEInstance(polymodel.PolyModel):
  load = ndb.FloatProperty()
  address = ndb.StringProperty()  # address of the service with port number e.g. ws://72.4.2.1:2345/
  zone = ndb.StringProperty()


class LoadBalancer(object):
  @staticmethod
  def nearest_zone(request):
    location = request.headers.get("X-AppEngine-CityLatLong")
    if location:
      location = tuple([float(x) for x in location.split(",")])
      dist = None
      for loc, zones in LOCATIONS.iteritems():
        d = HaversineDistance(location, loc)
        if not dist or d < dist:
          dist = d
          closest = zones
      return random.choice(closest)
    return random.choice([zone for l, z in LOCATIONS.iteritems() for zone in z])

  @staticmethod
  def load():
    """Return the current load."""
    pass

  @staticmethod
  def start_instance(instance_class):
    """Start a new instance with a given configuration."""
    pass

  @staticmethod
  def stop_instance(key):
    """Stop an instance with given datastore key."""
    pass

  @staticmethod
  def restart(instance_class=None):
    """Shutdown all instances and reboot, neccessary when
    setup and run scripts change. Restarts just those with instance_class
    if given otherwise restarts all instances."""
    pass

  @staticmethod
  def find(kind, request):
    """Get the most appropriate kind of instance for the given request."""
    return "ws://localhost:2345/"


class LoadBalanceHandler(webapp2.RequestHandler):
  def post(self):
    """POST handler used by the taskqueue api to update the loadbalancer with the heartbeat"""
    if not users.is_current_user_admin():
      raise AppError("Unauthorized.")

app = webapp2.WSGIApplication([
  (r"{}compute_engine/?.*".format(PREFIX), LoadBalanceHandler),
], debug=DEBUG)
