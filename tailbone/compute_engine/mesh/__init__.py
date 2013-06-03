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
from tailbone.compute_engine import LoadBalancer

import random
import string
import webapp2

from google.appengine.api import users
from google.appengine.ext import ndb


class TailboneMeshRoom(ndb.Model):
  ip = ndb.StringProperty()


def create_room():
  name = generate_word() + 'n' + generate_word()
  # Test to confirm the generated name doesn't exist
  room = TailboneMeshRoom.get_by_id(name)
  if not room:
    room = TailboneMeshRoom(id=name)
    room.put()
    return room
  return create_room()


def get_or_create_room(name):
  if name:
    room = TailboneMeshRoom.get(name)
    if not room:
      room = TailboneMeshRoom(id=name)
    return room
  return create_room()


class MeshHandler(BaseHandler):
  @as_json
  def get(self, name):
    # find the best fitting
    # turn = LoadBalancer.get('turn')
    # ws = LoadBalancer.get('websocket')
    room = get_or_create_room(name)
    return {
      "ip": "localhost",
      "name": room.key.id(),
    }

  @as_json
  def delete(self, name):
    if not users.is_current_user_admin():
      raise AppError('Unauthorized.')


app = webapp2.WSGIApplication([
  (r"/tailbone.mesh.js", compile_js([
    "tailbone/compute_engine/mesh/js/EventDispatcher.js",
    "tailbone/compute_engine/mesh/js/StateDrive.js",
    "tailbone/compute_engine/mesh/js/Node.js",
    "tailbone/compute_engine/mesh/js/Mesh.js",
  ], exports=[("tailbone.Mesh", "Mesh")])),
  (r"{}mesh/?(.*)".format(PREFIX), MeshHandler),
], debug=DEBUG)



# Gibberish generator modified from: https://github.com/greghaskins/gibberish
VOWELS = 'aeiou'
INITIAL_CONSONANTS = list(set(string.ascii_lowercase) - set(VOWELS)
                      # remove those easily confused with others
                      - set('qxc')
                      # add some crunchy clusters
                      | set(['bl', 'br', 'cl', 'cr', 'dr', 'fl',
                             'fr', 'gl', 'gr', 'pl', 'pr', 'sk',
                             'sl', 'sm', 'sn', 'sp', 'st', 'str',
                             'sw', 'tr', 'ch', 'sh'])
                      )
FINAL_CONSONANTS = list(set(string.ascii_lowercase) - set(VOWELS)
                    # remove the confusables
                    - set('qxcsj')
                    # crunchy clusters
                    | set(['ct', 'ft', 'mp', 'nd', 'ng', 'nk', 'nt',
                           'pt', 'sk', 'sp', 'ss', 'st', 'ch', 'sh'])
                    )

def generate_word():
    """Returns a random consonant-vowel-consonant pseudo-word."""
    return ''.join(random.choice(s) for s in (INITIAL_CONSONANTS,
                                              VOWELS,
                                              FINAL_CONSONANTS))
