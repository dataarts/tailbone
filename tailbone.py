"""
tailbone

Appengine abstract restful backend
"""

import datetime
import functools
import json
import logging
import os
import random
import re
import sys
import time
import webapp2
import yaml

from google.appengine import api
from google.appengine.api import channel
from google.appengine.ext import ndb
from google.appengine.ext import deferred


"""
Intention:
  Try to stay as direct to the appengine api where applicable so it is an easy transition if you
  need to extend this.
  Make the api abstract enough so that any javascript framework will do and so that the same
  frontend could be used with another backend that implements the same api calls.

Ideas:
  Scoping private/public
    Capital is public
    lowercase is private

  Open Questions:
    cron job to look for data inconsistencies to notify you if they come up
    so you can ban a user if they are being a problem by storing things in the data set incorrectly.

    Send a weekly summary email about statistical outliers and information in your database.

    Special names
      CreatedAt or created_at -> auto sets the created at property and can only be modified by the
      server.
      ModifiedAt or modified_at -> where the server sets when it was last modified.

    How do you do full text search?
      Searchable{Text} -> if name is searchable it adds this to the full text search api
      /api/search/model?q=text

    Realtime binding
      Todo = new tailbone.Model("todos");
      todos = Todo.query({name: "doug"});
      t = new Todo({name: "doug");
      t.$save()
      t.$delete()

      channel listeners bound to queries
      save checks all listened queries for a matching one
"""

# Custom Exceptions
class AppError(Exception):
  pass

class BreakError(Exception):
  pass

class LoginError(Exception):
  pass


def current_user(required=False):
  u = api.users.get_current_user()
  if u:
    return u.user_id()
  if required:
    raise LoginError("User must be logged in.")
  return None

# Explicit Models
class ScopedExpando(ndb.Expando):
  owners__ = ndb.IntegerProperty(repeated=True)
  editors__ = ndb.IntegerProperty(repeated=True)
  def to_dict(self, *args, **kwargs):
    excluded = ["owners__","editors__"]
    if len(args) == 2:
      args[1] += exluded
    if kwargs.has_key("exclude"):
      kwargs["exclude"] += excluded
    else:
      kwargs["exclude"] = excluded
    result = super(ScopedExpando, self).to_dict(*args, **kwargs)
    # if the current user is owner return private attibutes too
    result["Id"] = self.key.id()
    return result

class users(ndb.Expando):
  def to_dict(self, *args, **kwargs):
    result = super(users, self).to_dict(*args, **kwargs)
    result["Id"] = self.key.id()
    return result

def json_extras(obj):
  """Extended json processing of types."""
  if hasattr(obj, "utctimetuple"):
    ms = time.mktime(obj.utctimetuple()) * 1000
    ms += getattr(obj, "microseconds", 0) / 1000
    return int(ms)
  return None

def as_json(func):
  """Returns json when callback in url"""
  @functools.wraps(func)
  def wrapper(self, *args, **kwargs):
    self.response.headers["Content-Type"] = "application/json"
    if DEBUG:
      self.response.headers["Access-Control-Allow-Origin"] = "*"
      self.response.headers["Access-Control-Allow-Methods"] = "POST,GET,PUT,PATCH,HEAD,OPTIONS"
      self.response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    else:
      api.namespace_manager.set_namespace(VERSION)
    try:
      resp = func(self, *args, **kwargs)
    except BreakError as e:
      return
    except AppError as e:
      resp = { "error": str(e) }
      logging.error(str(e))
    except LoginError as e:
      url = users.create_login_url(self.request.url)
      resp = {
        "error": str(e),
        "url": url
      }
      logging.error(str(e))
    except api.datastore_errors.BadArgumentError as e:
      resp = { "error": str(e) }
      logging.error(str(e))
    if not isinstance(resp, str):
      resp = json.dumps(resp, default=json_extras)
    callback = self.request.get("callback")
    if callback:
      self.response.headers["Content-Type"] = "text/javascript"
      resp = "%s(%s);" % (_callback, resp)
    self.response.out.write(resp)
  return wrapper

def reflective_create(cls, data):
  m = cls()
  for k,v in data.iteritems():
    m._default_indexed = True
    if type(v) in [str, unicode]:
      if len(bytearray(v, encoding="utf8")) >= 500:
        m._default_indexed = False
    elif type(v) == dict:
      subcls = unicode.encode(k, "ascii", errors="ignore")
      v = reflective_create(type(subcls, (ndb.Expando,), {}), v)
    elif type(v) in [int, float]:
      v = float(v)
    setattr(m, k, v)
  return m

def parse_body(self):
  if "application/json" in self.request.content_type:
    data = json.loads(self.request.body)
  else:
    # TODO: must do further processing this into an dict
    # TODO: must upload any FieldStorage objects to blobstore
    data = self.request.params
  return data or {}

def clean_data(data):
  # strips any disallowed names {id, _*, etc}
  disallowed = ["Id", "id", "key"]
  exceptions = ["Id"]
  for key in disallowed:
    if data.has_key(key):
      if key not in exceptions:
        logging.warn("Disallowed key {%s} passed in object creation." % key)
      del data[key]
  return data


def parse_id(id, data_id=None):
  try:
    id = int(id)
  except:
    pass
  if data_id != None:
    if id:
      if data_id != id:
        raise AppError("Url id {%s} must match object id {%s}" % (id, data_id))
    else:
      id = data_id
  return id

re_filter = re.compile(r"^([\w\-.]+)(!=|==|=|<=|>=|<|>)(.+)$")
re_composite_filter = re.compile(r"^(AND|OR)\((.*)\)$")
re_split = re.compile(r",\W*")

def construct_filter(filter_str):
  m = re_composite_filter.match(filter_str)
  if m:
    filters = [construct_filter(f) for f in re_split.split(m.group(2))]
    if m.group(1) == "AND":
      return ndb.query.AND(*filters)
    else:
      return ndb.query.OR(*filters)
  m = re_filter.match(filter_str)
  if m:
    name, opsymbol, value = m.groups()
    if value == "true":
      value = True
    elif value == "false":
      value = False
    else:
      try:
        value = float(value)
      except:
        pass
    if opsymbol == "==":
      opsymbol = "="
    return ndb.query.FilterNode(name, opsymbol, value)
  if re_split.match(filter_str):
    return construct_filter("AND({})".format(filter_str))
  raise AppError("Filter format is unsupported: {}".format(filter_str))

def construct_order(cls, o):
  neg = True if o[0] == "-" else False
  o = o[1:] if neg else o
  if hasattr(cls, o):
    p = getattr(cls, o)
  else:
    p = ndb.GenericProperty(o)
  return -p if neg else p

def construct_query(cls, filters, orders):
  q = cls.query()
  q = q.filter(*[construct_filter(f) for f in filters])
  # TODO(doug) correctly auto append orders when necessary like on a multiselect
  q = q.order(*[construct_order(cls,o) for o in orders])
  return q

class RestfulHandler(webapp2.RequestHandler):
  @as_json
  def options(self, model, id):
    pass
  @as_json
  def get(self, model, id):
    # TODO(doug) does the model name need to be ascii encoded since types don't support utf-8
    cls = type(model.lower(), (ScopedExpando,), {})
    if id:
      id = parse_id(id)
      m = cls.get_by_id(id)
      if not m:
        raise AppError("There does not exists a %s with id %s" % (model, id))
      return m.to_dict()
    else:
      page_size = int(self.request.get("page_size", default_value=100))
      cursor = self.request.get("cursor")
      cursor = Cursor.from_websafe_string(cursor) if cursor else None
      projection = self.request.get("projection")
      filters = self.request.get_all("filter")
      orders = self.request.get_all("order")
      q = construct_query(cls, filters, orders)

      results, cursor, more = q.fetch_page(page_size=page_size, cursor=cursor)
      self.response.headers["More"] = "true" if more else "false"
      if cursor:
        self.response.headers["Next-Cursor"] = cursor.urlsafe()
        self.response.headers["Prev-Cursor"] = cursor.reversed().urlsafe()
      return [m.to_dict() for m in results]
  def set_or_create(self, model, id):
    cls = type(model.lower(), (ScopedExpando,), {})
    data = parse_body(self)
    id = parse_id(id, data.get("Id"))
    clean_data(data)
    m = reflective_create(cls, data)
    if id:
      m.key = ndb.Key(model, id)
    m.put()
    return m.to_dict()
  @as_json
  def post(self, model, id):
    return self.set_or_create(model, id)
  @as_json
  def patch(self, model, id):
    # TODO: implement this differently to do partial update
    return self.set_or_create(model, id)
  @as_json
  def put(self, model, id):
    return self.set_or_create(model, id)
  @as_json
  def delete(self, model, id):
    if not id:
      raise AppError("Must provide an id.")
    id = parse_id(id)
    key = ndb.Key(model.lower(), id)
    key.delete()
    return {}

class LoginHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect(
        api.users.create_login_url(
          self.request.get("url", default_value="/")))

class LogoutHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect(
        api.users.create_logout_url(
          self.request.get("url", default_value="/")))

class UsersHandler(webapp2.RequestHandler):
  """
  GET /api/users/:id
  returns the user info
  GET /api/users/me
  returns the current user
  """
  @as_json
  def get(self, id):
    pass
  @as_json
  def put(self, id):
    u = current_user(required=True)
    if id != "me" and id != u:
      raise AppError("Id must be the current user_id or me.")
    m = users.get_by_id(u)
    update_model(m, self)
    return m
  def delete(self, id):
    """Delete the user"s account and all their associated data."""
    pass

class AccessHandler(webapp2.RequestHandler):
  """
  GET /api/access/model/:id
    See if you have access to this model.
  {
    owners:[user_id],
    editors:[],
  }

  PUT /api/access/model/:id
    Give user with id user_id access
  {
    owners:[user_id],
    editors:[],
  }
  """
  @as_json
  def get(self, model, id):
    pass
  @as_json
  def put(self, model, id):
    pass

class AdminHandler(webapp2.RequestHandler):
  """Admin routes"""
  @as_json
  def get(self, action):
    if not api.users.is_current_user_admin():
      raise LoginError("You must be an admin.")


#-----------------
# START Event code
#-----------------
class events(ndb.Model):
  NUM_SHARDS = 20
  name = ndb.StringProperty()
  shard_id = ndb.IntegerProperty()
  listeners = ndb.IntegerProperty(repeated=True)


def bind(user_key, name):
  event = events.query(events.listeners == user_key, events.name == name).get()
  if not event:
    def txn():
      shard_id = random.randint(0, events.NUM_SHARDS - 1)
      event_key = ndb.Key(events, "{}_{}".format(name, shard_id))
      event = event_key.get()
      if not event:
        event = events(name=name, shard_id=shard_id, key=event_key)
      event.listeners.append(user_key)
      event.put()
      return event
    event = ndb.transaction(txn)
  return event

def unbind(user_key, name=None):
  eventlist = events.query(events.listeners == user_key)
  if name:
    eventlist = eventlist.filter(events.name == name)
  modified = []
  for event in eventlist:
    def txn():
      event.listeners = [l for l in event.listeners if l != user_key]
      if event.listeners:
        event.put()
      else:
        event.key.delete()
    ndb.transaction(txn)
    modified.append(event.to_dict())
  return modified

def trigger(name, payload):
  msg = json.dumps({ "name": name,
                     "payload": payload })
  sent_to = set()
  for e in events.query(events.name == name):
    for l in e.listeners:
      if l not in sent_to:
        sent_to.add(l)
        deferred.defer(channel.send_message, str(l), msg)
  return sent_to


class ConnectedHandler(webapp2.RequestHandler):
  @as_json
  def post(self):
    client_id = self.request.get('from')
    try:
      client_id = int(client_id)
    except:
      pass
    logging.info("Connecting client id {}".format(client_id))


class DisconnectedHandler(webapp2.RequestHandler):
  @as_json
  def post(self):
    client_id = self.request.get('from')
    try:
      client_id = int(client_id)
    except:
      pass
    logging.info("Disconnecting client id {}".format(client_id))
    unbind(client_id)


class RebootHandler(webapp2.RequestHandler):
  @as_json
  def get(self):
    # remove all event bindings and
    # force all current listeners to close and reconnect.
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


class EventsHandler(webapp2.RequestHandler):
  @as_json
  def post(self):
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

# ---------------
# END Event Code
# ---------------


APP_YAML = yaml.load(open("app.yaml"))
# prefix is taken from parsing the app.yaml
PREFIX = "/api/"

# VERSION is used to set the namespace
VERSION = APP_YAML.get("version")
DEBUG = os.environ.get("SERVER_SOFTWARE", "").startswith("Dev")

app = webapp2.WSGIApplication([
  ("/_ah/channel/connected/", ConnectedHandler),
  ("/_ah/channel/disconnected/", DisconnectedHandler),
  (r"{}login".format(PREFIX), LoginHandler),
  (r"{}logout" .format(PREFIX), LogoutHandler),
  (r"{}admin/(.+)".format(PREFIX), AdminHandler),
  (r"{}users/(.*)".format(PREFIX), UsersHandler),
  (r"{}access/([^/]+)/?(.*)".format(PREFIX), AccessHandler),
  (r"{}events/.*".format(PREFIX), EventsHandler),
  (r"{}([^/]+)/(.*)".format(PREFIX), RestfulHandler),
  ], debug=DEBUG)




