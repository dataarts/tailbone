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

from tailbone import DEBUG, PREFIX

import logging
import random
import webapp2

from google.appengine.ext import ndb

# These are just random guesses based on the name I have no idea where they actually are.
LOCATIONS = {
  'us-central1-a': ndb.GeoPt(36.0156, 114.7378),
  'us-central1-b': ndb.GeoPt(36.0156, 114.7378),
  'us-central2-a': ndb.GeoPt(36.0156, 114.7378),
  'europe-west1-a': ndb.GeoPt(52.5233, 13.4127),
  'europe-west1-b': ndb.GeoPt(52.5233, 13.4127),
  'default': ndb.GeoPt(36.0156, 114.7378),
}

# Prefixing internal models with Tailbone to avoid clobbering when using RESTful API
class TailboneCEInstance(ndb.Expando):
  load = ndb.FloatProperty()
  address = ndb.StringProperty()  # address of the service with port number e.g. ws://72.4.2.1:2345/
  location = ndb.GeoPtProperty()
  zone = ndb.StringProperty()

  def _pre_put_hook(self):
    """Set the GeoPtProperty based on the zone string."""
    self.location = LOCATIONS.get(self.zone, LOCATIONS.get('default'))


class LoadBalancer(object):
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
    pass

app = webapp2.WSGIApplication([
  (r"{}compute_engine/?.*".format(PREFIX), LoadBalanceHandler),
], debug=DEBUG)
