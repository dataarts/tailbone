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

from tailbone import DEBUG
from tailbone import PREFIX
from tailbone import AppError
from tailbone import BaseHandler
from tailbone import as_json

import json
import logging
import time
import random
import webapp2

from google.appengine.api import channel
from google.appengine.api import memcache
from google.appengine.api import lib_config
from google.appengine.ext import ndb

SEPARATOR = "--"
RETRIES = 3


class _ConfigDefaults(object):
  def generate_client_id(request):
    return str(memcache.incr("tailbone_mesh_channel_uid", initial_value=1))


_config = lib_config.register("tailboneMeshChannel", _ConfigDefaults.__dict__)


def append_mesh_to_cid(mesh, client_id):
  return "{}{}{}".format(mesh, SEPARATOR, client_id)


def extract_mesh_from_cid(client_id):
  return client_id.split(SEPARATOR)[0]


class TailbonChannelMesh(ndb.Model):
  clients = ndb.StringProperty(repeated=True)


class ConnectedHandler(BaseHandler):
  @as_json
  @ndb.transactional(retries=RETRIES)
  def post(self):
    client_id = self.request.get('from')
    mesh_id = extract_mesh_from_cid(client_id)
    mesh = TailbonChannelMesh.get_by_id(mesh_id)
    if not mesh:
      mesh = TailbonChannelMesh(id=mesh_id)
    if client_id in mesh.clients:
      logging.error("Client id {} already in list".format(client_id))
      return
    peers = [cid for cid in mesh.clients]
    mesh.clients.append(client_id)
    mesh.put()
    # send connect
    channel.send_message(client_id, json.dumps([
      client_id, time.time(), json.dumps(['connect'] + peers)]))
    # send enter
    enter_msg = json.dumps(['enter', client_id])
    for cid in peers:
      channel.send_message(cid, json.dumps([
        cid, time.time(), enter_msg]))


class DisconnectedHandler(BaseHandler):
  @as_json
  @ndb.transactional(retries=RETRIES)
  def post(self):
    client_id = self.request.get('from')
    mesh_id = extract_mesh_from_cid(client_id)
    mesh = TailbonChannelMesh.get_by_id(mesh_id)
    if not mesh:
      logging.error("Mesh {} does not exist.".format(mesh_id))
      return
    if client_id not in mesh.clients:
      logging.error("Client id {} not in list".format(client_id))
      return
    mesh.clients.remove(client_id)
    if len(mesh.clients) == 0:
      mesh.key.delete()
    else:
      mesh.put()
    leave_msg = json.dumps(['leave', client_id])
    for cid in mesh.clients:
      channel.send_message(cid, json.dumps([
        cid, time.time(), leave_msg]))


class ChannelHandler(BaseHandler):
  @as_json
  def get(self, mesh_id, _):
    if mesh_id == "":
      raise AppError("Must specify mesh id.")
    client_id = append_mesh_to_cid(mesh_id, _config.generate_client_id(self.request))
    return {"token": channel.create_channel(str(client_id))}

  @as_json
  def post(self, mesh_id, client_id):
    if mesh_id == "":
      raise AppError("Must specify mesh id.")
    if client_id == "":
      raise AppError("Must specify client id.")
    clients, payload = json.loads(self.request.body)
    msg = json.dumps([client_id, time.time(), payload])
    logging.info(msg)
    for cid in clients:
      # TODO: assert client_id is in mesh_id
      channel.send_message(cid, msg)


app = webapp2.WSGIApplication([
  (r"{}channel/?([^/]*)/?([^/]*)".format(PREFIX), ChannelHandler),
], debug=DEBUG)


connected = webapp2.WSGIApplication([
  ("/_ah/channel/connected/", ConnectedHandler),
  ("/_ah/channel/disconnected/", DisconnectedHandler),
], debug=DEBUG)
