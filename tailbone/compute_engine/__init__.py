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

import json
import math
import os
import random
import sys
import webapp2

from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.api import urlfetch
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

credentials = AppAssertionCredentials(scope=",".join(SCOPES))
http = credentials.authorize(httplib2.Http(memcache))
compute = build("compute", API_VERSION, http=http)


def ApiUrl(*paths):
  """Construct compute engine api url."""
  return BASE_URL + "/".join(paths)


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
  status = ndb.StringProperty()  # READY, STARTING, ERROR, DISABLED

  def CalcLoad(stats):
    return stats.mem

  PARAMS = {
    "kind": "compute#instance",
    "name": "default",
    "zone": ApiUrl(PROJECT_ID, "zones", DEFAULT_ZONE),
    "image": ApiUrl("debian-cloud", "global", "images", "debian-7-wheezy-v20130515"),
    "machineTypes": ApiUrl(PROJECT_ID, "zones", DEFAULT_ZONE, "machineTypes", "n1-standard-1"),
    "networkInterfaces": [
      {
        "kind": "compute#networkInterface",
        "network": ApiUrl(PROJECT_ID, "global", "networks", "default"),
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
  def StartInstance(instance_class, zone=None):
    """Start a new instance with a given configuration."""
    # start instance
    # defer an update load call
    pass

  @staticmethod
  def StopInstance(instance):
    """Stop an instance."""
    # cancel update load defered call
    # stop instance
    pass

  @staticmethod
  def Find(instance_class, request):
    """Get the most appropriate instance for the given request."""
    zone = LoadBalancer.NearestZone(request)
    qry = instance_class.query(TailboneCEInstance.zone == zone)
    qry = qry.order(TailboneCEInstance.load)
    instance = qry.get()
    if not instance:
      instance = LoadBalancer.StartInstance(instance_class, zone)
    return instance or "ws://localhost:2345/"

  @staticmethod
  def DrainInstance(instance):
    """Drain a particular instance"""
    # TODO: should clear an instance first
    LoadBalancer.StopInstance(instance)
    pass

  @staticmethod
  def Drain(instance_class=None, zone=None):
    """Drain a set of instances"""
    pass

  @staticmethod
  def UpdateLoad(urlsafe_instance_key):
    """Check the load on a given instance."""
    key = ndb.Key(urlsafe=urlsafe_instance_key)
    instance = key.get()
    statsurl = "http://"+instance.ip+":8888"
    result = urlfetch.fetch(statsurl)
    if result.status_code == 200:
      stats = json.loads(result.content)
      load = instance.CalcLoad(stats)
      instance.load = load
      instance.put()

  @staticmethod
  def Rebalance():
    """Rebalance the current load."""
    groups = {}
    for instance in TailboneCEInstance.query():
      cls = instance._class_name()
      zone = instance.zone
      groups[cls] = groups[cls] or {}
      groups[cls][zone] = groups[cls][zone] or {}
      groups[cls][zone].append(instance)
    for cls, zonemap in groups.iteritems():
      for zone, items in zonemap.iteritems():
        # rebalance the items in this zone
        # if total load < x then drain one
        # if load > y add an instance to this zone
        # TODO: have rebalancer be aware of outages
        print(items)


class LoadBalanceHandler(webapp2.RequestHandler):
  def post(self):
    """POST handler used by the taskqueue api to update the loadbalancer with the heartbeat."""
    if not users.is_current_user_admin():
      raise AppError("Unauthorized.")

app = webapp2.WSGIApplication([
  (r"{}compute_engine/?.*".format(PREFIX), LoadBalanceHandler),
], debug=DEBUG)
