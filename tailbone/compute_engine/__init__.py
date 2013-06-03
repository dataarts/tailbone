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
  zone = ndb.StringProperty()
  load = ndb.FloatProperty()

class LoadBalancer(webapp2.RequestHandler):
  @classmethod
  def load():
    """Return the current load."""
    pass

  @classmethod
  def start_instance(configuration):
    """Start a new instance with a given configuration"""
    pass

  @classmethod
  def stop_instance(instance_id):
    pass

  def get(self):
    pass


app = webapp2.WSGIApplication([
  (r"{}compute_engine/?.*".format(PREFIX), LoadBalancer),
], debug=DEBUG)
