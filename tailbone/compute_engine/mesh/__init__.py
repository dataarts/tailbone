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

# shared resources and global variables
from tailbone import as_json, DEBUG, PREFIX, BaseHandler, compile_js, AppError
from tailbone.compute_engine import LoadBalancer, TailboneCEInstance
from tailbone.compute_engine.turn import TailboneTurnInstance

import os
import random
import string
import webapp2

from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.api import app_identity

APP_VERSION = os.environ.get("CURRENT_VERSION_ID", "").split('.')[0]
HOSTNAME = APP_VERSION + "-dot-" + app_identity.get_default_version_hostname()
WEBSOCKET_PORT = 2345
ROOM_EXPIRATION = 86400  # one day in seconds

mesh_script = open("tailbone/compute_engine/mesh/setup_and_run.sh").read()

# TODO: Use an image instead of a startup-script for downloading dependencies

# Prefixing internal models with Tailbone to avoid clobbering when using RESTful API
class TailboneMeshInstance(TailboneCEInstance):
  PARAMS = dict(TailboneCEInstance.PARAMS, **{
    "name": "websocket-id",
    "metadata": {
      "items": [
        {
          "key": "startup-script",
          "value": mesh_script,
        },
      ],
    }
  })


def room_name(name):
  return "tailbone-mesh-room-{}".format(name)


def get_or_create_room(request, name=None, num_words=2, seperator="."):
  if not name:
    name = []
    for i in range(num_words):
      name.append(generate_word())
    name = seperator.join(name)
  room = room_name(name)
  address = memcache.get(room)
  if not address:
    instance = LoadBalancer.find(TailboneMeshInstance, request)
    if not instance:
      raise AppError('Instance not yet ready, try again later.')
    address = "ws://{}:{}/{}".format(instance.address, WEBSOCKET_PORT, name)
    memcache.set(room, address, time=ROOM_EXPIRATION)
  return name, address


class MeshHandler(BaseHandler):
  @as_json
  def get(self, name):
    room, ws = get_or_create_room(self.request, name)
    # turn = LoadBalancer.find(TailboneTurnInstance, self.request)
    turn = None
    return {
      "ws": ws,
      "name": room,
      "turn": turn,
    }

  @as_json
  def delete(self, name):
    if not users.is_current_user_admin():
      raise AppError("Unauthorized.")
    if not name:
      raise AppError("Must provide name.")

EXPORTED_JAVASCRIPT = compile_js([
  "tailbone/compute_engine/mesh/js/EventDispatcher.js",
  "tailbone/compute_engine/mesh/js/StateDrive.js",
  "tailbone/compute_engine/mesh/js/Channel.js",
  "tailbone/compute_engine/mesh/js/SocketChannel.js",
  "tailbone/compute_engine/mesh/js/RTCChannel.js",
  "tailbone/compute_engine/mesh/js/Node.js",
  "tailbone/compute_engine/mesh/js/Mesh.js",
], ["Mesh"])

app = webapp2.WSGIApplication([
  (r"{}mesh/?(.*)".format(PREFIX), MeshHandler),
], debug=DEBUG)


# Gibberish generator modified from: https://github.com/greghaskins/gibberish
VOWELS = "aeiou"
INITIAL_CONSONANTS = list(set(string.ascii_lowercase) - set(VOWELS)
                      - set("qxc")
                      | set(["bl", "br", "cl", "cr", "dr", "fl",
                            "fr", "gl", "gr", "pl", "pr", "sk",
                            "sl", "sm", "sn", "sp", "st", "str",
                            "sw", "tr", "ch", "sh"])
                         )
FINAL_CONSONANTS = list(set(string.ascii_lowercase) - set(VOWELS)
                    - set("qxcsj")
                    | set(["ct", "ft", "mp", "nd", "ng", "nk", "nt",
                           "pt", "sk", "sp", "ss", "st", "ch", "sh"])
                       )


def generate_word():
    """Returns a random consonant-vowel-consonant pseudo-word."""
    return ''.join(random.choice(s) for s in (INITIAL_CONSONANTS,
                                              VOWELS,
                                              FINAL_CONSONANTS))
