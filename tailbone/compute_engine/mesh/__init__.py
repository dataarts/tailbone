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
from tailbone import as_json, BaseHandler, compile_js, AppError
from tailbone import config
from tailbone.compute_engine import LoadBalancer, TailboneCEInstance
from tailbone.compute_engine import turn

import base64
import os
import random
import string
import webapp2

from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.api import app_identity
from google.appengine.api import lib_config 

APP_VERSION = os.environ.get("CURRENT_VERSION_ID", "").split('.')[0]
HOSTNAME = APP_VERSION + "-dot-" + app_identity.get_default_version_hostname()
WEBSOCKET_PORT = 2345

mesh_script = open("tailbone/compute_engine/mesh/setup_and_run.sh").read()

class _ConfigDefaults(object):
  ROOM_EXPIRATION = 86400  # one day in seconds

  def generate_room_name():
    return generate_word() + "." + generate_word()


_config = lib_config.register('mesh', _ConfigDefaults.__dict__)

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


def room_hash(name):
  return "tailbone-mesh-room-{}".format(base64.b64encode(name))

def unique_name():
  name = _config.generate_room_name()
  room = room_hash(name)
  address = memcache.get(room)
  if address:
    return unique_name()
  return name, room, address

def get_or_create_room(request, name=None):
  if not name:
    name, room, address = unique_name()
  else:
    room = room_hash(name)
    address = memcache.get(room)
  if not address:
    if config.DEBUG:
      class DebugInstance(object):
        address = "localhost"
      instance = DebugInstance()
    else:
      instance = LoadBalancer.find(TailboneMeshInstance, request)
    if not instance:
      raise AppError('Instance not yet ready, try again later.')
    address = "ws://{}:{}/{}".format(instance.address, WEBSOCKET_PORT, name)
    memcache.set(room, address, time=_config.ROOM_EXPIRATION)
  return name, address


class MeshHandler(BaseHandler):
  @as_json
  def get(self, name):
    room, ws = get_or_create_room(self.request, name)
    # ts = LoadBalancer.find(turn.TailboneTurnInstance, self.request)
    username = self.request.get("username", generate_word())
    username, password = turn.credentials(username)
    ts = None
    return {
      "ws": ws,
      "name": room,
      "turn": ts,
      "username": username,
      "password": password,
    }

  @as_json
  def delete(self, name):
    if not config.is_current_user_admin():
      raise AppError("Unauthorized.")
    if not name:
      raise AppError("Must provide name.")

EXPORTED_JAVASCRIPT = compile_js([
  "tailbone/compute_engine/mesh/js/EventDispatcher.js",
  "tailbone/compute_engine/mesh/js/StateDrive.js",
  "tailbone/compute_engine/mesh/js/Channel.js",
  "tailbone/compute_engine/mesh/js/SocketChannel.js",
  "tailbone/compute_engine/mesh/js/SocketMultiplexer.js",
  "tailbone/compute_engine/mesh/js/RTCChannel.js",
  "tailbone/compute_engine/mesh/js/Node.js",
  "tailbone/compute_engine/mesh/js/Peers.js",
  "tailbone/compute_engine/mesh/js/Mesh.js",
], ["Mesh"])

app = webapp2.WSGIApplication([
  (r"{}mesh/?(.*)".format(config.PREFIX), MeshHandler),
], debug=config.DEBUG)


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
