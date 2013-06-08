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


# TODO:
# be aware of outages in how instances are started up
# ability to drain a mesh and migrate users without a hiccup in service
# report back usage more accurately than number of connected users possibly with diff API

from tailbone import DEBUG, PREFIX, AppError

import logging
import math
import os
import random
import sys
import webapp2

from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel

sys.path.insert(0, 'tailbone/compute_engine/dependencies.zip')
from oauth2client.appengine import AppAssertionCredentials
import httplib2
from apiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/devstorage.read_write"]
# These are just random guesses based on the name I have no idea where they actually are.
LOCATIONS = {
  (36.0156, 114.7378): ["us-central1-a", "us-central1-b", "us-central2-a"],
  (52.5233, 13.4127): ["europe-west1-a", "europe-west1-b"],
}
API_VERSION = "v1beta15"
BASE_URL = "https://www.googleapis.com/compute/{}/projects/".format(API_VERSION)
PROJECT_ID = os.environ.get("PROJECT_ID", "")
DEFAULT_ZONE = "us-central1-a"
DEFAULT_IMAGE = "debian-7-wheezy-v20130515"

credentials = AppAssertionCredentials(scope=",".join(SCOPES))
http = credentials.authorize(httplib2.Http(memcache))
compute = build("compute", API_VERSION, http=http)


def ApiUrl(*paths, **kwargs):
  """Construct compute engine api url."""
  project = kwargs.get("project")
  if not project:
    project = PROJECT_ID
  return BASE_URL + project + "/" + "/".join(paths)


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


# Prefixing internal models with Tailbone to avoid clobbering when using RESTful API
class TailboneCEInstance(polymodel.PolyModel):
  name = ndb.StringProperty()
  load = ndb.FloatProperty(repeated=True)
  address = ndb.StringProperty()  # address of the service with port number e.g. ws://72.4.2.1:2345/
  zone = ndb.StringProperty()

  PARAMS = {
    "kind": "compute#instance",
    "name": "default",
    "zone": ApiUrl("zones", DEFAULT_ZONE),
    "image": ApiUrl("global", "images", DEFAULT_IMAGE, project="debian-cloud"),
    "machineTypes": ApiUrl("zones", DEFAULT_ZONE, "machineTypes", "n1-standard-1"),
    "networkInterfaces": [
      {
        "kind": "compute#networkInterface",
        "network": ApiUrl("global", "networks", "default"),
        "accessConfigs": [
          {
            "type": "ONE_TO_ONE_NAT",
            "name": "External NAT"
          }
        ],
      }
    ],
    "serviceAccounts": [
      {
        "kind": "compute#serviceAccount",
        "email": "default",
        "scopes": SCOPES
      }
    ], 
  }


class LoadBalancer(object):

  @staticmethod
  def NearestZone(request):
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
  def Load():
    """Return the current load."""
    pass

  @staticmethod
  def StartInstance(instance_class, zone=None):
    """Start a new instance with a given configuration."""
    pass

  @staticmethod
  def StopInstance(key):
    """Stop an instance with given datastore key."""
    pass

  @staticmethod
  def Restart(instance_class=None, zone=None, force=False):
    """Shutdown all instances and reboot, neccessary when
    setup and run scripts change. Restarts just those with instance_class
    if given otherwise restarts all instances."""
    pass

  @staticmethod
  def Find(instance_class, request):
    """Get the most appropriate instance for the given request."""
    zone = LoadBalancer.nearest_zone(request)
    instance_class.query(zone=zone)
    return "ws://localhost:2345/"

  @staticmethod
  def DrainInstance(key):
    """Drain a particular instance"""
    pass

  @staticmethod
  def Drain(instance_class=None, zone=None):
    """Drain a set of instances"""
    pass

  @staticmethod
  def Rebalance():
    """Rebalance the current load."""
    groups = {}
    for instance in TailboneCEInstance.all():
      cls = instance._class_name()
      zone = instance.zone
      groups[cls] = groups[cls] or {}
      groups[cls][zone] = groups[cls][zone] or {}
      groups[cls][zone].append(instance)
    for cls, zonemap in groups.iteritems():
      for zone, items in zonemap.iteritems():
        # rebalance the items in this zone
        print(items)




class LoadBalanceHandler(webapp2.RequestHandler):
  def post(self):
    """POST handler used by the taskqueue api to update the loadbalancer with the heartbeat."""
    if not users.is_current_user_admin():
      raise AppError("Unauthorized.")
    logging.warn(httplib2)

app = webapp2.WSGIApplication([
  (r"{}compute_engine/?.*".format(PREFIX), LoadBalanceHandler),
], debug=DEBUG)
