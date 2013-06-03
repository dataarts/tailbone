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
from tailbone import as_json, DEBUG, PREFIX, BaseHandler, compile_js
from tailbone.compute_engine import LoadBalancer

import webapp2

from google.appengine.api import memcache
from google.appengine.ext import ndb

## GET /api/mesh/
# {
#   "ip": "172.2.34.1",
#   "name": "sweetpotato"
#   "id": "aDFKiuFEN34jDFwlfj"
# }
# GET /api/mesh/sweetpotato
# {
#   "ip": "172.2.34.1",
#   "name": "sweetpotato"
#   "id": "aDFKiuFEN34jDFwlfj"
# }
# can connect ip address or use as turn stun server
# var m = new Mesh();
# var m = new Mesh("sweetpotato");
# m.broadcast("hello");
# m.nodes = []
# remember to extend the maximum number of open files


# class TailboneRoom(ndb.Model):
#   ip = ndb.StringProperty()


class MeshHandler(BaseHandler):
  @as_json
  def get(self, name):
    # find the best fitting
    # turn = LoadBalancer.get('turn')
    # ws = LoadBalancer.get('websocket')
    return {
      "ip": "localhost",
      "name": "test"
    }


app = webapp2.WSGIApplication([
  (r"/tailbone.mesh.js", compile_js([
    "tailbone/compute_engine/mesh/js/EventDispatcher.js",
    "tailbone/compute_engine/mesh/js/StateDrive.js",
    "tailbone/compute_engine/mesh/js/Node.js",
    "tailbone/compute_engine/mesh/js/Mesh.js",
  ], exports=[("tailbone.Mesh", "Mesh")])),
  (r"{}mesh/?(.*)".format(PREFIX), MeshHandler),
], debug=DEBUG)
