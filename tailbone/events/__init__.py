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
from tailbone import *

import json
import logging
import random
import webapp2

from google.appengine.api import channel
from google.appengine.ext import ndb

# Event Code
# ----------
# Not really used directly so you can mostly ignore this section. Has some disabilities as a result
# of being on the channel api rather than directly via sockets. Google the channel api and app
# engine to learn more.

# The storage and look up of listeners is sharded to reduce conflicts in adding and removing
# listeners during simultaneous edits.
class events(ndb.Model):
  NUM_SHARDS = 20
  name = ndb.StringProperty()
  shard_id = ndb.IntegerProperty()
  listeners = ndb.IntegerProperty(repeated=True)

def bind(user_key, name):
  event = events.query(events.listeners == user_key, events.name == name).get()
  if event:
    return event
  @ndb.transactional
  def create():
    shard_id = random.randint(0, events.NUM_SHARDS - 1)
    event_key = ndb.Key(events, "{}_{}".format(name, shard_id))
    event = event_key.get()
    if not event:
      event = events(name=name, shard_id=shard_id, key=event_key)
    event.listeners.append(user_key)
    event.put()
    return event
  return create()

def unbind(user_key, name=None):
  eventlist = events.query(events.listeners == user_key)
  if name:
    eventlist = eventlist.filter(events.name == name)
  modified = []
  @ndb.tasklet
  @ndb.transactional
  def remove_from(event):
    event.listeners = [l for l in event.listeners if l != user_key]
    if event.listeners:
      yield event.put_async()
    else:
      yield event.key.delete_async()
    raise ndb.Return(event.to_dict())
  return eventlist.map(remove_from)

def trigger(name, payload):
  msg = json.dumps({ "name": name,
                     "payload": payload })
  def send(event):
    for l in event.listeners:
      channel.send_message(str(l), msg)
    return event.listeners
  q = events.query(events.name == name)
  return reduce(lambda x,y: x+y, q.map(send), [])

class ConnectedHandler(BaseHandler):
  @as_json
  def post(self):
    client_id = self.request.get('from')
    try:
      client_id = int(client_id)
    except:
      pass
    logging.info("Connecting client id {}".format(client_id))


class DisconnectedHandler(BaseHandler):
  @as_json
  def post(self):
    client_id = self.request.get('from')
    try:
      client_id = int(client_id)
    except:
      pass
    logging.info("Disconnecting client id {}".format(client_id))
    unbind(client_id)

# Remove all event bindings and force all current listeners to close and reconnect.
class RebootHandler(BaseHandler):
  @as_json
  def get(self):
    logging.info("REBOOT")
    send_to = set()
    to_delete = set()
    msg = json.dumps({ "reboot": True })
    for e in events.query():
      for l in e.listeners:
        if l not in send_to:
          sent_to.add(l)
      to_delete.add(e.key)
    def delete():
      ndb.delete_multi(to_delete)
    ndb.transaction(delete)
    for l in send_to:
      deferred.defer(channel.send_message, str(l), msg)


class EventsHandler(BaseHandler):
  @as_json
  def post(self):
    # TODO(doug): add better client_id generation
    data = parse_body(self)
    method = data.get("method")
    client_id = data.get("client_id")
    if method == "token":
      return {"token": channel.create_channel(str(client_id))}
    elif method == "bind":
      bind(client_id, data.get("name"))
    elif method == "unbind":
      unbind(client_id, data.get("name"))
    elif method == "trigger":
      trigger(data.get("name"), data.get("payload"))

EXPORTED_JAVASCRIPT = compile_js([
  "tailbone/events/events.js",
], ["events"])

app = webapp2.WSGIApplication([
  (r"{}events/.*".format(PREFIX), EventsHandler),
  ], debug=DEBUG)

connected = webapp2.WSGIApplication([
  ("/_ah/channel/connected/", ConnectedHandler),
  ("/_ah/channel/disconnected/", DisconnectedHandler),
  ], debug=DEBUG)
