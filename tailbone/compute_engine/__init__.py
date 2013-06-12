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

from tailbone import AppError
from tailbone import as_json
from tailbone import BaseHandler
from tailbone import DEBUG
from tailbone import parse_body
from tailbone import PREFIX

import importlib
import inspect
import json
import math
import os
import random
import sys
import uuid
import webapp2

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel

sys.path.insert(0, "tailbone/compute_engine/dependencies.zip")
from oauth2client.appengine import AppAssertionCredentials
import httplib2
from apiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/devstorage.read_write"]
# These are just random guesses based on the name I have no idea where they actually are.
LOCATIONS = {
  (36.0156, 114.7378): ["us-central1-a", "us-central1-b", "us-central2-a"],
  (52.5233, 13.4127): ["europe-west1-a", "europe-west1-b"],
}
ZONES = [zone for l, z in LOCATIONS.iteritems() for zone in z]
API_VERSION = "v1beta15"
BASE_URL = "https://www.googleapis.com/compute/{}/projects/".format(API_VERSION)
# TODO: throw error on use if no PROJECT_ID defined
PROJECT_ID = os.environ.get("PROJECT_ID", "")
DEFAULT_ZONE = "us-central1-a"

credentials = AppAssertionCredentials(scope=",".join(SCOPES))
http = credentials.authorize(httplib2.Http(memcache))
compute = build("compute", API_VERSION, http=http)


def api_url(*paths):
  """Construct compute engine api url."""
  return BASE_URL + "/".join(paths)


def haversine_distance(location1, location2):
  """Method to calculate Distance between two sets of Lat/Lon."""
  lat1, lon1 = location1
  lat2, lon2 = location2
  #Calculate Distance based in Haversine Formula
  dlat = math.radians(lat2-lat1)
  dlon = math.radians(lon2-lon1)
  a = math.sin(dlat/2) * math.sin(dlat/2) + \
      math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
      math.sin(dlon/2) * math.sin(dlon/2)
  c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
  # c * 6371  # Earth's radius in km
  return c


class InstanceStatus(object):
  READY = "ready"
  STARTING = "starting"
  STOPPING = "stopping"
  ERROR = "error"
  DISABLED = "disabled"
  DRAINING = "draining"


# Prefixing internal models with Tailbone to avoid clobbering when using RESTful API
class TailboneCEInstance(polymodel.PolyModel):
  name = ndb.StringProperty()
  load = ndb.FloatProperty()
  address = ndb.StringProperty()  # address of the service with port number e.g. ws://72.4.2.1:2345/
  zone = ndb.StringProperty()
  status = ndb.StringProperty()  # READY, STARTING, ERROR, DISABLED

  def calc_load(stats):
    return stats.mem

  PARAMS = {
    "kind": "compute#instance",
    "name": "default",
    "zone": api_url(PROJECT_ID, "zones", DEFAULT_ZONE),
    "image": api_url("debian-cloud", "global", "images", "debian-7-wheezy-v20130515"),
    "machineTypes": api_url(PROJECT_ID, "zones", DEFAULT_ZONE, "machineTypes", "n1-standard-1"),
    "networkInterfaces": [
      {
        "kind": "compute#networkInterface",
        "network": api_url(PROJECT_ID, "global", "networks", "default"),
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
  def nearest_zone(request):
    location = request.headers.get("X-AppEngine-CityLatLong")
    if location:
      location = tuple([float(x) for x in location.split(",")])
      dist = None
      for loc, zones in LOCATIONS.iteritems():
        d = haversine_distance(location, loc)
        if not dist or d < dist:
          dist = d
          closest = zones
      return random.choice(closest)
    return random.choice(ZONES)

  @staticmethod
  def start_instance(instance_class, zone=None):
    """Start a new instance with a given configuration."""
    # start instance
    # defer an update load call
    name = "{}-{}".format(instance_class.__name__, uuid.uuid4())
    instance = instance_class()
    instance.PARAMS.update({
      "name": name
    })
    compute.instances().insert(
      project=PROJECT_ID, zone=instance.PARAMS.get("zone"), body=instance.PARAMS).execute()
    instance.put()

  @staticmethod
  def stop_instance(instance):
    """Stop an instance."""
    # cancel update load defered call
    # stop instance
    compute.instances().delete(
      project=PROJECT_ID, zone=instance.zone, instance=instance.name).execute()
    instance.key.delete()

  @staticmethod
  def find(instance_class, request):
    """Get the most appropriate instance for the given request."""
    zone = LoadBalancer.nearest_zone(request)
    query = instance_class.query(TailboneCEInstance.zone == zone)
    query = query.order(TailboneCEInstance.load)
    instance = query.get()
    if not instance:
      instance = LoadBalancer.start_instance(instance_class, zone)
    return instance or "ws://localhost:2345/"

  @staticmethod
  def drain_instance(instance):
    """Drain a particular instance"""
    # TODO: should clear an instance first
    instance.status = InstanceStatus.DISABLED
    LoadBalancer.stop_instance(instance)

  @staticmethod
  def drain(instance_class=None, zone=None):
    """Drain a set of instances"""
    query = instance_class.query(TailboneCEInstance.zone == zone)
    for instance in query:
      LoadBalancer.drain_instance(instance)

  @staticmethod
  def update_load(urlsafe_instance_key):
    """Check the load on a given instance."""
    key = ndb.Key(urlsafe=urlsafe_instance_key)
    instance = key.get()
    statsurl = "http://"+instance.ip+":8888"
    result = urlfetch.fetch(statsurl)
    if result.status_code == 200:
      stats = json.loads(result.content)
      load = instance.calc_load(stats)
      instance.load = load
      instance.put()

  @staticmethod
  def rebalance():
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


class LoadBalancerApi(object):
  @staticmethod
  def start_instance(request, instance_class, zone=None):
    """Start an instance."""
    if zone:
      assert zone in ZONES
    module_name, class_name = instance_class.rsplit(".", 1)
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return LoadBalancer.start_instance(cls, zone)

  @staticmethod
  def drain_instance(request, urlsafe_instance_key):
    """Drain an instance."""
    instance = ndb.Key(urlsafe=urlsafe_instance_key)
    LoadBalancer.drain_instance(instance)

  @staticmethod
  def echo(request, message):
    """Echo a message."""
    return message


class LoadBalanceHandler(BaseHandler):
  """Admin handler for the admin panel console."""
  @as_json
  def get(self):
    methods = inspect.getmembers(LoadBalancerApi, predicate=inspect.isfunction)
    return [(k, inspect.getargspec(v).args[1:], v.__doc__) for k, v in methods]

  @as_json
  def post(self):
    """POST handler as JSON-RPC."""
    data = parse_body(self)
    method = getattr(LoadBalancerApi, data.get("method"))
    params = data.get("params", [])
    params.insert(0, self.request)
    resp = method(*params)
    return resp


app = webapp2.WSGIApplication([
  (r"{}compute_engine/?.*".format(PREFIX), LoadBalanceHandler),
], debug=DEBUG)
