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

# Static template configurations to be passed to start_instance
CONFIGURATIONS = {
  'WEBSOCKET': {
    'kind': 'websocket',
    'startup-script': 'tailbone/compute_engine/mesh/setup_and_run_ws.sh'
  },
  'TURN': {
    'kind': 'turn',
    'startup-script': 'tailbone/compute_engine/mesh/setup_and_run_turn.sh'
  },
}


class TailboneCEInstance(ndb.Expando):
  kind = ndb.StringProperty()  # websocket, turn, etc
  ip = ndb.StringProperty()
  zone = ndb.GeoPtProperty()
  load = ndb.FloatProperty()


class LoadBalancer(webapp2.RequestHandler):
  # Supported instance types
  WEBSOCKET = 'websocket'
  TURN = 'turn'

  @staticmethod
  def load():
    """Return the current load."""
    pass

  @staticmethod
  def start_instance(configuration):
    """Start a new instance with a given configuration"""
    pass

  @staticmethod
  def stop_instance(instance_id):
    """Stop an instance with given instance_id"""
    pass

  @staticmethod
  def restart():
    """Shutdown all instances and reboot, neccessary when
    setup and run scripts change"""
    pass

  @staticmethod
  def find(kind, request):
    """Get the most appropriate kind of instance for the given request."""
    return "localhost"

  def get(self):
    """GET handler used by the taskqueue api to update the loadbalancer with the heartbeat"""
    pass


app = webapp2.WSGIApplication([
  (r"{}compute_engine/?.*".format(PREFIX), LoadBalancer),
], debug=DEBUG)
