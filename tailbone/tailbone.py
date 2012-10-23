"""
tailbone

Appengine abstract restful backend
"""

import cgi
import datetime
import functools
import json
import logging
import os
import random
import re
import string
import sys
import time
import urllib
import webapp2
import yaml

from google.appengine import api
from google.appengine.api import channel
from google.appengine.api.images import get_serving_url_async
from google.appengine.api.images import delete_serving_url
from google.appengine.ext import blobstore
from google.appengine.ext import deferred
from google.appengine.ext import ndb
from google.appengine.ext import testbed
from google.appengine.ext.webapp import blobstore_handlers

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

def convert_num_to_str(num):
  s = ""
  num = str(num)
  i = 0
  l = len(num)
  letters = string.ascii_letters
  while True:
    if i == l-1:
      s += letters[int(num[i])]
      break
    if i >= l:
      break
    x = num[i]
    n = int(x+num[i+1])
    if n < 52:
      s += letters[n]
      i += 2
    else:
      s += letters[int(x)]
      i += 1
  return s

def convert_str_to_num(s):
  num = ""
  for x in s:
    num += str(string.ascii_letters.index(x))
  return num

def current_user(required=False):
  u = api.users.get_current_user()
  if u:
    return convert_num_to_str(u.user_id())
  if required:
    raise LoginError("User must be logged in.")
  return None

re_public = re.compile(r"^[A-Z].*")

# Explicit Models
class ScopedExpando(ndb.Expando):
  owners__ = ndb.StringProperty(repeated=True)
  editors__ = ndb.StringProperty(repeated=True)
  def to_dict(self, *args, **kwargs):
    excluded = ["owners__","editors__"]
    if len(args) == 2:
      args[1] += exluded
    if kwargs.has_key("exclude"):
      kwargs["exclude"] += excluded
    else:
      kwargs["exclude"] = excluded
    result = super(ScopedExpando, self).to_dict(*args, **kwargs)
    u = current_user()
    if u and (u in self.owners__ or u in self.editors__):
      # private and public properties
      pass
    else:
      # public properties only
      for k in result.keys():
        if not re_public.match(k):
          del result[k]
    result["Id"] = self.key.id()
    return result

class users(ndb.Expando):
  def to_dict(self, *args, **kwargs):
    result = super(users, self).to_dict(*args, **kwargs)
    result["Id"] = self.key.id()
    return result

def json_extras(obj):
  """Extended json processing of types."""
  if hasattr(obj, "get_result"): # RPC
    return obj.get_result()
  if hasattr(obj, "utctimetuple"): # datetime
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
      api.namespace_manager.set_namespace(NAMESPACE)
    try:
      resp = func(self, *args, **kwargs) or {}
    except BreakError as e:
      return
    except AppError as e:
      resp = { "error": str(e) }
      if api.app_identity.get_application_id() != testbed.DEFAULT_APP_ID:
        logging.error(str(e))
    except LoginError as e:
      url = api.users.create_login_url(self.request.url)
      resp = {
        "error": str(e),
        "url": url
      }
      if api.app_identity.get_application_id() != testbed.DEFAULT_APP_ID:
        logging.error(str(e))
    except api.datastore_errors.BadArgumentError as e:
      resp = { "error": str(e) }
      if api.app_identity.get_application_id() != testbed.DEFAULT_APP_ID:
        logging.error(str(e))
    if not isinstance(resp, str) and not isinstance(resp, unicode):
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
    if type(v) in [unicode, str]:
      if len(bytearray(v, encoding="utf8")) >= 500:
        m._default_indexed = False
    elif type(v) == dict:
      subcls = unicode.encode(k, "ascii", errors="ignore")
      v = reflective_create(type(subcls, (ndb.Expando,), {}), v)
    elif type(v) in [int, float]:
      v = float(v)
    setattr(m, k, v)
  return m

re_json = re.compile(r"^application/json", re.IGNORECASE)

def parse_body(self):
  if re_json.match(self.request.content_type):
    data = json.loads(self.request.body)
  else:
    data = {}
    for k,v in self.request.POST.items():
      if isinstance(v, cgi.FieldStorage):
        raise AppError("Files should be uploaded seperately as their own form to /api/files/.")
        # TODO: writing to blobstore in this way will have an upper limit on size of upload
        # try doing this maybe with the async deferred handler or with creating an /upload redirct
        filename = api.files.blobstore.create(mime_type="application/octet-stream")
        with api.files.open(filename, 'a') as f:
          f.write(v.file.read())
        api.files.finalize(filename)
        v = str(api.files.blobstore.get_blob_key(filename))
      if data.has_key(k):
        current = data[k]
        if isinstance(current, list):
          current.append(v)
        else:
          data[k] = [current,v]
      else:
        data[k] = v
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

def convert_value(value):
  if value == "true":
    value = True
  elif value == "false":
    value = False
  else:
    try:
      value = float(value)
    except:
      pass
  return value

def convert_opsymbol(opsymbol):
  if opsymbol == "==":
    opsymbol = "="
  return opsymbol

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
    return ndb.query.FilterNode(name, convert_opsymbol(opsymbol), convert_value(value))
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

def construct_filter_json(f):
  t = type(f)
  if t == list:
    if f[0] == "AND":
      filters = [construct_filter_json(f) for f in f[1:]]
      return ndb.query.AND(*filters)
    elif f[0] == "OR":
      filters = [construct_filter_json(f) for f in f[1:]]
      return ndb.query.OR(*filters)
    else:
      name, opsymbol, value = f
      return ndb.query.FilterNode(name, convert_opsymbol(opsymbol), convert_value(value))
  else:
    return f

def construct_query_from_json(cls, filters, orders):
  q = cls.query()
  if filters:
    q = q.filter(construct_filter_json(filters))
  if orders:
    q = q.order(*[construct_order(cls,o) for o in orders])
  return q

def construct_query_from_url_args(cls, filters, orders):
  q = cls.query()
  q = q.filter(*[construct_filter(f) for f in filters])
  # TODO(doug) correctly auto append orders when necessary like on a multiselect
  q = q.order(*[construct_order(cls,o) for o in orders])
  return q

def query(self, cls):
  params = self.request.get("params")
  if params:
    params = json.loads(params)
    page_size = params.get("page_size", 100)
    cursor = params.get("cursor")
    filters = params.get("filter")
    orders = params.get("order")
    q = construct_query_from_json(cls, filters, orders)
  else:
    page_size = int(self.request.get("page_size", default_value=100))
    cursor = self.request.get("cursor")
    projection = self.request.get("projection")
    filters = self.request.get_all("filter")
    orders = self.request.get_all("order")
    q = construct_query_from_url_args(cls, filters, orders)
  cursor = Cursor.from_websafe_string(cursor) if cursor else None

  results, cursor, more = q.fetch_page(page_size=page_size, cursor=cursor)
  self.response.headers["More"] = "true" if more else "false"
  if cursor:
    self.response.headers["Next-Cursor"] = cursor.urlsafe()
    self.response.headers["Prev-Cursor"] = cursor.reversed().urlsafe()
  return [m.to_dict() for m in results]

class RestfulHandler(webapp2.RequestHandler):
  @as_json
  def get(self, model, id):
    # TODO(doug) does the model name need to be ascii encoded since types don't support utf-8
    cls = users if model == "users" else type(model.lower(), (ScopedExpando,), {})
    if id:
      if model == "users":
        if id == "me":
          id = current_user(required=True)
      id = parse_id(id)
      m = cls.get_by_id(id)
      if not m:
        if model == "users":
          m = users()
          m.key = ndb.Key("users", id)
          # m.put()
        else:
          raise AppError("No {} with id {}.".format(model, id))
      return m.to_dict()
    else:
      return query(self, cls)
  def set_or_create(self, model, id):
    u = current_user(required=True)
    if model == "users":
      if not (id == "me" or id == "" or id == u):
        raise AppError("Id must be the current " +
            "user_id or me. User {} tried to modify user {}.".format(u,id))
      id = u
      cls = users
    else:
      cls = type(model.lower(), (ScopedExpando,), {})
    data = parse_body(self)
    id = parse_id(id, data.get("Id"))
    clean_data(data)
    if id and model != "users":
      old_model = cls.get_by_id(id)
      if old_model and u not in old_model.owners__ and u not in old_model.editors__:
        raise AppError("You do not have sufficient privileges.")
    m = reflective_create(cls, data)
    if id:
      m.key = ndb.Key(model, id)
    if model != "users":
      if u not in m.owners__ and u not in m.editors__:
        m.owners__.append(u)
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
    if model == "users":
      u = current_user(required=True)
      if id != "me" and id != u:
        raise AppError("Id must be the current " +
            "user_id or me. User {} tried to modify user {}.".format(u,id))
      id = u
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
  def setaccess(self, model, id):
    return {}
  @as_json
  def put(self, model, id):
    return self.setaccess(model, id)
  @as_json
  def post(self, model, id):
    return self.setaccess(model, id)

class AdminHandler(webapp2.RequestHandler):
  """Admin routes"""
  @as_json
  def get(self, action):
    if not api.users.is_current_user_admin():
      raise LoginError("You must be an admin.")

re_image = re.compile(r"image/(png|jpeg|jpg|webp|gif|bmp|tiff|ico)", re.IGNORECASE)

def blob_info_to_dict(blob_info):
  d = {}
  for prop in ["content_type", "creation", "filename", "size"]:
    d[prop] = getattr(blob_info, prop)
  key = blob_info.key()
  if re_image.match(blob_info.content_type):
    d["image_url"] = get_serving_url_async(key)
  d["Id"] = str(key)
  return d

class FilesHandler(blobstore_handlers.BlobstoreDownloadHandler,
    blobstore_handlers.BlobstoreUploadHandler):
  @as_json
  def get(self, key):
    if key == "":
      return {
          "upload_url": blobstore.create_upload_url("/api/files/upload")
          }
    key = str(urllib.unquote(key))
    blob_info = blobstore.BlobInfo.get(key)
    if not blob_info:
      self.error(404)
    else:
      self.send_blob(blob_info)
    raise BreakError

  @as_json
  def post(self, _):
    raise AppError("You must make a GET call to /api/files to get a POST url.")

  @as_json
  def put(self, _):
    raise AppError("PUT is not supported for the files api.")

  @as_json
  def delete(self, key):
    key = blobstore.BlobKey(str(urllib.unquote(key)))
    blob_info = blobstore.BlobInfo.get(key)
    if not blob_info:
      self.error(404)
    else:
      blob_info.delete()
      if re_image.match(blob_info.content_type):
        delete_serving_url(key)
    return {}

class FilesUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
  @as_json
  def post(self):
    return [blob_info_to_dict(b) for b in self.get_uploads()]

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

class JsTestHandler(webapp2.RequestHandler):
  def get(self):
    if not DEBUG:
      self.error(404)
      return
    self.response.out.write("""
<!doctype html>
<html>
  <head>
    <title></title>
    <link rel="stylesheet" href="http://code.jquery.com/qunit/qunit-git.css">
  </head>
  <body>
  <div id="qunit"></div>
  <script src="http://code.jquery.com/qunit/qunit-git.js" type="text/javascript"></script>
  <script src="/_ah/channel/jsapi" type="text/javascript" charset="utf-8"></script>
  <script src="/tailbone.js" type="text/javascript" charset="utf-8"></script>
  <script>
    {}
  </script>
  </body>
</html>
""".format(open("test_tailbone.js").read()))

class UploadTestHandler(webapp2.RequestHandler):
  def get(self):
    if not DEBUG:
      self.error(404)
      return
    self.response.out.write("""
<!doctype html>
<html>
  <head>
    <title></title>
  </head>
  <body>
  <form action="{}" method="POST" enctype="multipart/form-data">
  <input type="file" name="file" />
  <input type="submit" name="submit" value="Submit" />
  </form>
  </body>
</html>
""".format(blobstore.create_upload_url("/api/files/upload")))

# prefix is taken from parsing the app.yaml
PREFIX = "/api/"

NAMESPACE = os.environ.get("NAMESPACE", "")
DEBUG = os.environ.get("SERVER_SOFTWARE", "").startswith("Dev")

app = webapp2.WSGIApplication([
  (r"{}upload_test.html".format(PREFIX), UploadTestHandler),
  (r"{}js_test.html".format(PREFIX), JsTestHandler),
  (r"{}login".format(PREFIX), LoginHandler),
  (r"{}logout" .format(PREFIX), LogoutHandler),
  (r"{}admin/(.+)".format(PREFIX), AdminHandler),
  (r"{}files/upload".format(PREFIX), FilesUploadHandler),
  (r"{}files/?(.*)".format(PREFIX), FilesHandler),
  (r"{}access/([^/]+)/?(.*)".format(PREFIX), AccessHandler),
  (r"{}events/.*".format(PREFIX), EventsHandler),
  (r"{}([^/]+)/?(.*)".format(PREFIX), RestfulHandler),
  ], debug=DEBUG)

connected = webapp2.WSGIApplication([
  ("/_ah/channel/connected/", ConnectedHandler),
  ("/_ah/channel/disconnected/", DisconnectedHandler),
  ], debug=DEBUG)


