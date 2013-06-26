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

import os
import random
import string
import webapp2

from google.appengine.api import users
from google.appengine.api import app_identity
from google.appengine.ext import ndb

APP_VERSION = os.environ.get("CURRENT_VERSION_ID", "").split('.')[0]
HOSTNAME = APP_VERSION + "-dot-" + app_identity.get_default_version_hostname()
WEBSOCKET_PORT = 2345

websocket_script = open("tailbone/compute_engine/mesh/setup_and_run_ws.sh").read()
turn_script = open("tailbone/compute_engine/mesh/setup_and_run_turn.sh").read()


# Prefixing internal models with Tailbone to avoid clobbering when using RESTful API
class TailboneWebsocketInstance(TailboneCEInstance):
  PARAMS = dict(TailboneCEInstance.PARAMS, **{
    "name": "websocket-id",
    "metadata": {
      "items": [
        {
          "key": "startup-script",
          "value": websocket_script,
        },
      ],
    }
  })


# Prefixing internal models with Tailbone to avoid clobbering when using RESTful API
class TailboneTurnInstance(TailboneCEInstance):
  PARAMS = dict(TailboneCEInstance.PARAMS, **{
    "name": "turn-id",
    "metadata": {
      "items": [
        {
          "key": "startup-script",
          "value": turn_script,
        },
      ],
    }
  })


# Prefixing internal models with Tailbone to avoid clobbering when using RESTful API
class TailboneMeshRoom(ndb.Model):
  """TODO: add a taskqueue callback to be executed in the future to delete yourself
  if a connection is not made to this room after x amount of time.
  This should be executed in websocket.py when not in debug mode.
  Similar callback from websocket.py must be created for both when someone first enters a room
  and when the last person leaves."""
  address = ndb.StringProperty()
  created_at = ndb.DateTimeProperty(auto_now_add=True)
  in_use = ndb.BooleanProperty(default=False)


def create_room(request, name=None, num_words=2, seperator="."):
  room = None
  if not name:
    name = []
    for i in range(num_words):
      name.append(generate_word())
    name = seperator.join(name)
    # Test to confirm the generated name doesn't exist
    room = TailboneMeshRoom.get_by_id(name)
  if not room:
    # TODO: put the room creation in a @ndb.transaction
    instance = LoadBalancer.find(TailboneWebsocketInstance, request)
    if not instance:
      raise AppError('Instance not yet ready, try again later.')
    address = "ws://{}:{}/{}".format(instance.address, WEBSOCKET_PORT, name)
    room = TailboneMeshRoom(id=name, address=address)
    room.put()
    return room
  return create_room(request)


def get_or_create_room(request, name):
  if name:
    room = TailboneMeshRoom.get_by_id(name)
    if not room:
      room = create_room(request, name)
    return room
  return create_room(request)


class MeshHandler(BaseHandler):
  @as_json
  def get(self, name):
    room = get_or_create_room(self.request, name)
    turn = LoadBalancer.find(TailboneTurnInstance, self.request)
    return {
      "ws": room.address,
      "name": room.key.id(),
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
