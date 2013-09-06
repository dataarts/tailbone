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
from tailbone import parse_body
from tailbone import config
from tailbone import DEBUG
from tailbone import PREFIX
from tailbone import build_service

import datetime
import importlib
import inspect
import json
import logging
import math
import os
import random
import re
import sys
import time
import uuid
import webapp2

from google.appengine.api import app_identity
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.ext import deferred
from google.appengine.ext.ndb import polymodel

from apiclient.errors import HttpError

STARTUP_SCRIPT_BASE = """#!/bin/bash

# update open files limit
ulimit -n 10000

# install deps
apt-get install -y build-essential python-dev

# load reporter
curl -O http://psutil.googlecode.com/files/psutil-0.6.1.tar.gz
tar xvfz psutil-0.6.1.tar.gz
cd psutil-0.6.1
python setup.py install
cd ..
rm -rf psutil-0.6.1
rm psutil-0.6.1.tar.gz
cat >load_reporter.py <<EOL
%s
EOL
python load_reporter.py &

""" % (open("tailbone/compute_engine/load_reporter.py").read(),)

SCOPES = ["https://www.googleapis.com/auth/compute",
          "https://www.googleapis.com/auth/devstorage.read_write"]

API_VERSION = "v1beta15"
BASE_URL = "https://www.googleapis.com/compute/{}/projects/".format(API_VERSION)
# TODO: throw error on use if no PROJECT_ID defined
PROJECT_ID = app_identity.get_application_id()
DEFAULT_ZONE = "us-central1-a"
DEFAULT_TYPE = "n1-standard-1"
# DEFAULT_TYPE = "f1-micro"  # needs a boot image defined
STATS_PORT = 8888

SECONDS = 1
MINUTES = 60*SECONDS
DRAIN_DELAY = 30*MINUTES
REBALANCE_DELAY = 2*MINUTES
STARTING_STATUS_DELAY = 20*SECONDS
STATUS_DELAY = 1*MINUTES

POSITIONS = {
  "us": (36.0156, -114.7378),
  "europe": (52.5233, 13.4127),
  "asia": (30, 100),
}

def isoparse(s):
  d, tz = s.split(".")
  d = datetime.datetime.strptime(d, "%Y-%m-%dT%H:%M:%S")
  hr, mn = [int(x) for x in tz[-6:].split(":")]
  tz = datetime.timedelta(hours=hr,minutes=mn)
  return d + tz


def get_locations():
  req = webapp2.get_request()
  locations = req.environ.get("LOCATIONS")
  if locations:
    return locations
  locations = memcache.get("LOCATIONS")
  if locations:
    req.environ["LOCATIONS"] = locations
    return locations
  compute = compute_api()
  resp = compute.zones().list(project=PROJECT_ID).execute()
  locations = {}
  for zone in resp.get("items", []):
    # zone is up
    status = zone.get("status")
    if status != "UP":
      continue

    # zone not down for maintence
    now = datetime.datetime.now()
    timebuf = datetime.timedelta(days=1)
    maintenance = False
    for win in zone.get("maintenanceWindows", []):
      begin = isoparse(win.get("beginTime"))
      begin = begin - timebuf
      end = isoparse(win.get("endTime"))
      end = end + timebuf
      if now > begin and now < end:
        maintenance = True
        break
    if maintenance:
      continue

    # add zone to list
    name = zone.get("name")
    n = name.split("-")[0]
    pos = POSITIONS.get(n)
    if not pos:
      logging.warn("Location not found {} : {}".format(name, pos))
      continue
    l = locations.get(n)
    if not l:
      l = {"location": pos, "zones": []}
    l["zones"].append(name)
    locations[n] = l

  req.environ["LOCATIONS"] = locations
  memcache.set("LOCATIONS", locations, time=datetime.timedelta(hours=6).total_seconds())
  return locations


def compute_api():
  return build_service("compute", API_VERSION, SCOPES)


def api_url(*paths):
  """Construct compute engine api url."""
  return BASE_URL + "/".join(paths)


def rfc1035(name):
  return "-".join(l.lower() for l in re.findall("[A-Z][^A-Z]*", name))


def unrfc1035(name):
  return "".join(l.capitalize() for l in name.split("-"))


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


def class_to_string(cls):
  path = cls.__module__ + "." + cls.__name__
  return path


def string_to_class(str):
  module_name, class_name = str.rsplit(".", 1)
  module = importlib.import_module(module_name)
  cls = getattr(module, class_name)
  return cls


def _blocking_call(gce_service, response):
  """Blocks until the operation status is done for the given operation."""

  status = response['status']
  while status != 'DONE' and response:
    time.sleep(2)
    operation_id = response['name']

    # Identify if this is a per-zone resource
    if 'zone' in response:
      zone_name = response['zone'].split('/')[-1]
      request = gce_service.zoneOperations().get(
          project=PROJECT_ID,
          operation=operation_id,
          zone=zone_name)
    else:
      request = gce_service.globalOperations().get(
           project=PROJECT_ID, operation=operation_id)

    response = request.execute()
    if response:
      status = response['status']
  return response


class InstanceStatus(object):
  PENDING = "PENDING"
  RUNNING = "RUNNING"
  STAGING = "STAGING"
  STOPPING = "STOPPING"
  TERMINATED = "TERMINATED"
  DRAINING = "DRAINING"
  ERROR = "ERROR"
  UNKNOWN = "UNKNOWN"


# Prefixing internal models with Tailbone to avoid clobbering when using RESTful API
class TailboneCEInstance(polymodel.PolyModel):
  load = ndb.FloatProperty(default=0)
  address = ndb.StringProperty()  # address of the service with port number e.g. ws://72.4.2.1:2345/
  zone = ndb.StringProperty()
  status = ndb.StringProperty(default=InstanceStatus.PENDING)
  pool = ndb.KeyProperty()

  @staticmethod
  def calc_load(stats):
    """Calculate load value 0 to 1 from the stats object."""
    return stats.get("mem", 0)

  SOURCE_SNAPSHOT = None

  PARAMS = {
    "kind": "compute#instance",
    "name": "default",
    "zone": api_url(PROJECT_ID, "zones", DEFAULT_ZONE),
    "image": api_url("debian-cloud", "global", "images", "debian-7-wheezy-v20130515"),
    "machineType": api_url(PROJECT_ID, "zones", DEFAULT_ZONE, "machineTypes", DEFAULT_TYPE),
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


def rebalance_pool(urlsafe_pool_key):
  """Rebalance a pool based on load."""
  pool = ndb.Key(urlsafe=urlsafe_pool_key).get()
  if not pool:
    logging.error("Pool no longer exists {}".format(urlsafe_pool_key))
    return
  query = TailboneCEInstance.query()
  query = query.filter(TailboneCEInstance.pool == pool.key)
  query = query.filter(TailboneCEInstance.status.IN([
    InstanceStatus.RUNNING,
    InstanceStatus.PENDING,
    InstanceStatus.STAGING,
  ]))
  load = [i.load for i in query]
  size = len(load)
  if size > pool.max_size:
    LoadBalancer.decrease_pool(pool, size)
  elif size < pool.min_size:
    LoadBalancer.increase_pool(pool, size)
  elif size > 0:
    avg_load = sum(load) / size
    if avg_load < 0.2:
      LoadBalancer.decrease_pool(pool, size)
    elif avg_load > 0.7:
      LoadBalancer.increase_pool(pool, size)
  name = "rebalance_pool_{}_{}".format(pool.key.urlsafe(), int(time.time()))
  deferred.defer(rebalance_pool, pool.key.urlsafe(), _countdown=REBALANCE_DELAY, _name=name)


class TailboneCEPool(polymodel.PolyModel):
  min_size = ndb.IntegerProperty(default=1)
  max_size = ndb.IntegerProperty(default=10)
  instance_type = ndb.StringProperty()
  region = ndb.StringProperty()

  def instance(self):
    """Pick an instance from this pool."""
    query = TailboneCEInstance.query(TailboneCEInstance.pool == self.key,
                                     TailboneCEInstance.status == InstanceStatus.RUNNING)
    instances = [i for i in query]
    if instances:
      return random.choice(instances)
    return None
    # query = query.order(TailboneCEInstance.load)
    # return query.get()

  def size(self):
    query = TailboneCEInstance.query()
    query = query.filter(TailboneCEInstance.pool == self.key)
    size = query.filter(TailboneCEInstance.status.IN(
      [InstanceStatus.RUNNING,
       InstanceStatus.STAGING,
       InstanceStatus.PENDING])).count()
    return size


def remove_draining_instance(urlsafe_key):
  instance = ndb.Key(urlsafe=urlsafe_key).get()
  if instance.status == InstanceStatus.DRAINING:
    # remove instance
    LoadBalancer.stop_instance(instance)


def update_instance_status(urlsafe_key):
  instance = ndb.Key(urlsafe=urlsafe_key).get()
  if not instance:
    return
  if instance.status == InstanceStatus.DRAINING:
    return
  info = None
  if instance.status == InstanceStatus.RUNNING:
    # check load
    address = "http://{}:{}".format(instance.address, STATS_PORT)
    try:
      resp = urlfetch.fetch(url=address,
                            method=urlfetch.GET,
                            deadline=30)
      if resp.status_code == 200:
        stats = json.loads(resp.content)
        instance.load = instance.calc_load(stats)
        instance.put()
      else:
        instance.status = InstanceStatus.UNKNOWN
        instance.put()
    except Exception:
      instance.status = InstanceStatus.UNKNOWN
      instance.put()

    name = "update_instance_status_{}_{}".format(urlsafe_key, int(time.time()))
    deferred.defer(update_instance_status, urlsafe_key, _countdown=STATUS_DELAY, _name=name)
    return

  try:
    info = compute_api().instances().get(
      project=PROJECT_ID, zone=instance.zone,
      instance=instance.key.id()).execute()
  except HttpError as e:
    logging.info("Instance no longer exists, remove it.")
    logging.error(e)
    LoadBalancer.fill_pool(instance.pool.get())
    instance.key.delete()
    return
  logging.info("Instance status {}".format(info))
  status = info.get("status")
  if status == InstanceStatus.RUNNING:
    instance.status = status
    instance.address = info["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
    instance.put()
    name = "update_instance_status_{}_{}".format(urlsafe_key, int(time.time()))
    deferred.defer(update_instance_status, urlsafe_key, _countdown=STATUS_DELAY, _name=name)
  elif status in [InstanceStatus.PENDING, InstanceStatus.STAGING]:
    name = "update_instance_status_{}_{}".format(urlsafe_key, int(time.time()))
    deferred.defer(update_instance_status, urlsafe_key, _countdown=STARTING_STATUS_DELAY, _name=name)
  elif status in [InstanceStatus.STOPPING, InstanceStatus.TERMINATED]:
    LoadBalancer.stop_instance(instance, False)
  else:
    logging.error("Unexpected instance status: {}\n{}.".format(status, info))


class LoadBalancer(object):

  @staticmethod
  def nearest_zone():
    request = webapp2.get_request()
    location = request.headers.get("X-AppEngine-CityLatLong")
    if location:
      location = tuple([float(x) for x in location.split(",")])
      dist = None
      region = None
      closest = None
      locations = get_locations()
      for r, obj in locations.iteritems():
        loc = obj["location"]
        zones = obj["zones"]
        d = haversine_distance(location, loc)
        if dist is None or d < dist:
          dist = d
          closest = zones
          region = r
      return region, random.choice(closest)
    locations = get_locations()
    region = random.choice(locations.keys())
    return region, random.choice(locations[region]["zones"])

  @staticmethod
  def start_instance(pool):
    """Start a new instance with a given configuration."""
    # start instance
    # defer an update load call
    instance_class = string_to_class(pool.instance_type)
    name = rfc1035(instance_class.__name__)
    # max length of a name is 63
    name = "{}-{}".format(name, uuid.uuid4())[:63]
    instance = instance_class(id=name)
    instance.pool = pool.key
    locations = get_locations()
    instance.zone = random.choice(locations[pool.region]["zones"])

    compute = compute_api()
    if compute:
      def update_zone(s):
        return re.sub(r"\/zones\/([^/]*)",
                      "/zones/{}".format(instance.zone),
                      s)
      # create disk from source snapshot
      if instance.SOURCE_SNAPSHOT:
        operation = compute.disks().insert(
          project=PROJECT_ID, zone=instance.zone, body={
            "name": name,
            "sizeGb": 10,
            "sourceSnapshot": instance.SOURCE_SNAPSHOT,
          }).execute()
        _blocking_call(compute, operation)
        instance.PARAMS.update({
          "disks": [{
            "kind": "compute#attachedDisk",
            "boot": True,
            "type": "PERSISTENT",
            "mode": "READ_WRITE",
            "deviceName": name,
            "zone": update_zone(instance.PARAMS.get("zone")),
            "source": api_url(PROJECT_ID, "zones", instance.zone, "disks", name),
          }],
        })

      instance.PARAMS.update({
        "name": name,
        "zone": update_zone(instance.PARAMS.get("zone")),
        "machineType": update_zone(instance.PARAMS.get("machineType")),
      })
      operation = compute.instances().insert(
        project=PROJECT_ID, zone=instance.zone, body=instance.PARAMS).execute()
      logging.info("Create instance operation {}".format(operation))
      instance.status = operation.get("status")
      name = "update_instance_status_{}_{}".format(instance.key.urlsafe(), int(time.time()))
      deferred.defer(update_instance_status, instance.key.urlsafe(), _countdown=STARTING_STATUS_DELAY, _name=name)
    else:
      logging.warn("No compute api defined.")
      raise AppError("No compute api defined.")

    # finally put the instance after the resource has been created
    instance.put()

  @staticmethod
  def stop_instance(instance):
    """Stop an instance."""
    # cancel update load defered call
    # stop instance
    # TODO: need some way of clearing externally assciated instances
    compute = compute_api()
    if compute:
      name = instance.key.id()
      if instance.SOURCE_SNAPSHOT:
        compute.disks().delete(
          project=PROJECT_ID, zone=instance.zone, disk=name).execute()
      compute.instances().delete(
        project=PROJECT_ID, zone=instance.zone, instance=name).execute()
    else:
      logging.warn("No compute api defined.")
      raise AppError("No compute api defined.")
    instance.key.delete()

  @staticmethod
  def drain_instance(instance):
    """Drain a particular instance"""
    instance.status = InstanceStatus.DRAINING
    instance.put()
    name = "remove_draining_instance_{}_{}".format(instance.key.urlsafe(), int(time.time()))
    deferred.defer(remove_draining_instance, instance.key.urlsafe(), _countdown=DRAIN_DELAY, _name=name)

  @staticmethod
  def find(instance_class):
    """Return an instance of this instance type from the nearest pool or create it."""
    if DEBUG:
      # check to make sure we can access the api before we do anything
      compute_api()
    region, zone = LoadBalancer.nearest_zone()
    instance_str = class_to_string(instance_class)
    pool = LoadBalancer.get_or_create_pool(instance_str, region)

    instance = pool.instance()
    if instance and instance.address:
      return instance
    raise AppError("Instance not yet ready, please try again.")

  @staticmethod
  def fill_pool(pool):
    compute = compute_api()
    if compute:
      # find existing instances
      instance_class = string_to_class(pool.instance_type)
      name_match = ".*{}.*".format(rfc1035(instance_class.__name__))
      name_filter = "name eq {}".format(name_match)
      size = 0
      locations = get_locations()
      for zone in locations[pool.region]["zones"]:
        resp = compute.instances().list(project=PROJECT_ID,
                                        zone=zone,
                                        filter=name_filter).execute()
        logging.info("List of instances {}".format(resp))
        items = resp.get("items", [])
        for info in items:
          status = info.get("status")
          # if instance is new or running add it to the pool
          if status in [InstanceStatus.RUNNING, InstanceStatus.PENDING, InstanceStatus.STAGING]:
            instance_id = info.get("name")
            instance = instance_class.get_by_id(instance_id)
            if not instance:
              instance = instance_class(id=instance_id)
              instance.zone = info.get("zone").split("/")[-1]
              instance.status = status
              instance.address = info["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
              instance.pool = pool.key
              instance.put()
              name = "update_instance_status_{}_{}".format(instance.key.urlsafe(), int(time.time()))
              deferred.defer(update_instance_status, instance.key.urlsafe(), _countdown=STARTING_STATUS_DELAY, _name=name)
            size += 1
      # start any additional instances need to meet pool min_size
      for i in range(pool.min_size - size):
        LoadBalancer.start_instance(pool)

  @staticmethod
  def get_or_create_pool(instance_class_str, region):
    # see if this pool already exists
    query = TailboneCEPool.query(TailboneCEPool.region == region,
                                 TailboneCEPool.instance_type == instance_class_str)
    pool = query.get()
    # create it if it does not
    if not pool:
      pool = TailboneCEPool(region=region, instance_type=instance_class_str)
      pool.put()
      # start rebalancer
      name = "rebalance_pool_{}_{}".format(pool.key.urlsafe(), int(time.time()))
      deferred.defer(rebalance_pool, pool.key.urlsafe(), _countdown=REBALANCE_DELAY, _name=name)
      LoadBalancer.fill_pool(pool)
    return pool

  @staticmethod
  def increase_pool(pool, current_size):
    """Double pool size."""
    new_size = int(min(pool.max_size, current_size * 2))
    toadd = new_size - current_size
    if toadd <= 0:
      return {}
    # Find any draining instances and add back in
    query = TailboneCEInstance.query()
    query = query.filter(TailboneCEInstance.pool == pool.key)
    query = query.filter(TailboneCEInstance.status == InstanceStatus.DRAINING)
    for i in query:
      if toadd <= 0:
        break
      i.status = InstanceStatus.RUNNING
      i.put()
      toadd -= 1
    # start any additionally needed instances
    for i in range(toadd):
      LoadBalancer.start_instance(pool)
    return {}

  @staticmethod
  def decrease_pool(pool, current_size):
    """Half pool size."""
    new_size = int(max(pool.min_size, round(current_size * 0.8)))
    if current_size != new_size:
      dropped = current_size - new_size
      query = TailboneCEInstance.query()
      query = query.filter(TailboneCEInstance.pool == pool.key)
      query = query.filter(TailboneCEInstance.status == InstanceStatus.RUNNING)
      query = query.order(TailboneCEInstance.load)
      instances = query.fetch(dropped)
      for i in instances:
        LoadBalancer.drain_instance(i)
    return {}


class LoadBalancerApi(object):
  # @staticmethod
  # def fill_pool(request, instance_class_str, region):
  #   """Start a new instance pool."""
  #   return LoadBalancer.get_or_create_pool(instance_class_str, region)

  # @staticmethod
  # def increase_pool(request, urlsafe_pool_key):
  #   """Double pool size."""
  #   pool = ndb.Key(urlsafe=urlsafe_pool_key).get()
  #   size = pool.size()
  #   return LoadBalancer.increase_pool(pool, size)

  # @staticmethod
  # def decrease_pool(request, urlsafe_pool_key):
  #   """Half pool size."""
  #   pool = ndb.Key(urlsafe=urlsafe_pool_key).get()
  #   size = pool.size()
  #   return LoadBalancer.decrease_pool(pool, size)

  # @staticmethod
  # def resize_pool(request, params):
  #   """Update a pools params."""
  #   pass

  @staticmethod
  def list_instances(request):
    """List instances."""
    compute = compute_api()
    items = []
    locations = get_locations()
    zones = [zone for l, z in locations.iteritems() for zone in z["zones"]]
    for zone in zones:
      resp = compute.instances().list(project=PROJECT_ID,
                                      zone=zone).execute()
      items.append(resp)
    return items

  @staticmethod
  def echo(request, message):
    """Echo a message."""
    return message

  @staticmethod
  def test(request):
    """Nearest zone."""
    return LoadBalancer.nearest_zone()

  @staticmethod
  def set_pool_constraints(request, urlsafe_pool_key, min_size, max_size):
    min_size = int(min_size)
    max_size = int(max_size)
    pool = ndb.Key(urlsafe=urlsafe_pool_key).get()
    pool.min_size = min_size 
    pool.max_size = max_size 
    pool.put()
    return pool


class LoadBalanceAdminHandler(BaseHandler):
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
  (r"{}compute_engine/?.*".format(PREFIX), LoadBalanceAdminHandler),
], debug=DEBUG)
