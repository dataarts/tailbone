# Appengine abstract restful backend
# Intention:
#   Try to stay as direct to the appengine api where applicable so it is an easy transition if you
#   need to extend this.
#   Make the api abstract enough so that any javascript framework will do and so that the same
#   frontend could be used with another backend that implements the same api calls.
#
# Ideas:
#   Scoping private/public
#     Capital is public
#     lowercase is private
#
#   Open Questions:
#     cron job to look for data inconsistencies to notify you if they come up
#     so you can ban a user if they are being a problem by storing things in the data set incorrectly.
#
#     Send a weekly summary email about statistical outliers and information in your database.
#
#     Special names
#       CreatedAt or created_at -> auto sets the created at property and can only be modified by the
#       server.
#       ModifiedAt or modified_at -> where the server sets when it was last modified.
#
#     How do you do full text search?
#       Searchable{Text} -> if name is searchable it adds this to the full text search api
#       /api/search/model?q=text
#
#     Realtime binding
#       Todo = new tailbone.Model("todos");
#       todos = Todo.query({name: "doug"});
#       t = new Todo({name: "doug");
#       t.$save()
#       t.$delete()
#
#       channel listeners bound to queries
#       save checks all listened queries for a matching one

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
from google.appengine.api import urlfetch
from google.appengine.api.images import get_serving_url_async
from google.appengine.api.images import delete_serving_url
from google.appengine.ext import blobstore
from google.appengine.ext import deferred
from google.appengine.ext import ndb
from google.appengine.ext import testbed
from google.appengine.ext.webapp import blobstore_handlers

# Custom Exceptions
class AppError(Exception):
  pass

class BreakError(Exception):
  pass

class LoginError(Exception):
  pass


re_public = re.compile(r"^[A-Z].*")

# Model
# -----
# A modifed Expando class that all models derive from, this allows app engine to work as an
# arbitrary document store for your json objects as well as scope the public private nature of
# objects based on the capitolization of the property.
class ScopedExpando(ndb.Expando):
  owners = ndb.StringProperty(repeated=True)

  def is_owner(self, u):
    try:
      owners = self.owners
    except:
      return False
    if u and u in owners:
      return True
    return False

  def to_dict(self, *args, **kwargs):
    excluded = ["owners"]
    if len(args) == 2:
      args[1] += exluded
    if kwargs.has_key("exclude"):
      kwargs["exclude"] += excluded
    else:
      kwargs["exclude"] = excluded
    result = super(ScopedExpando, self).to_dict(*args, **kwargs)
    if self.is_owner(current_user()):
      # private and public properties
      result["owners"] = self.owners
    else:
      # public properties only
      for k in result.keys():
        if not re_public.match(k):
          del result[k]
    result["Id"] = self.key.id()
    return result

# User
# ----
# User is an special model that can only be written to by the google account owner.
class users(ndb.Expando):
  def to_dict(self, *args, **kwargs):
    result = super(users, self).to_dict(*args, **kwargs)
    u = current_user()
    if u and u == self.key.id():
      pass
    else:
      for k in result.keys():
        if not re_public.match(k):
          del result[k]
    result["Id"] = self.key.id()
    return result

# Extensions to the jsonifying of python results
def json_extras(obj):
  """Extended json processing of types."""
  if hasattr(obj, "get_result"): # RPC
    return obj.get_result()
  if hasattr(obj, "utctimetuple"): # datetime
    ms = time.mktime(obj.utctimetuple()) * 1000
    ms += getattr(obj, "microseconds", 0) / 1000
    return int(ms)
  return None

# Decorator to return the result of a function as json. It supports jsonp by default.
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
      resp = func(self, *args, **kwargs)
      if resp == None:
        resp = {}
    except BreakError as e:
      return
    except LoginError as e:
      self.response.set_status(401)
      url = api.users.create_login_url(self.request.url)
      resp = {
        "error": e.__class__.__name__,
        "message": e.message,
        "url": url
      }
      if api.app_identity.get_application_id() != testbed.DEFAULT_APP_ID:
        logging.error(str(e))
    except (AppError, api.datastore_errors.BadArgumentError,
        api.datastore_errors.BadRequestError) as e:
      self.response.set_status(400)
      resp = { "error": e.__class__.__name__, "message": e.message }
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

# BaseHandler for error handling
class BaseHandler(webapp2.RequestHandler):
  def handle_exception(self, exception, debug):
    # Log the error.
    logging.exception(exception)

    # If the exception is a HTTPException, use its error code.
    # Otherwise use a generic 500 error code.
    if isinstance(exception, webapp2.HTTPException):
      self.response.set_status(exception.code)
    else:
      self.response.set_status(500)

    return {"error": str(exception)}

# Reflectively instantiate a class given some data parsed by the restful json POST. If the size of
# an object is larger than 500 characters it cannot be indexed. Otherwise everything else is. In the
# future there may be a way to express what should be indexed or searchable, but not yet.
def reflective_create(cls, data):
  m = cls()
  for k,v in data.iteritems():
    m._default_indexed = True
    t = type(v)
    if t in [unicode, str]:
      if len(bytearray(v, encoding="utf8")) >= 500:
        m._default_indexed = False
    elif t == dict:
      subcls = unicode.encode(k, "ascii", errors="ignore")
      v = reflective_create(type(subcls, (ndb.Expando,), {}), v)
    elif t in [int, float]:
      v = float(v)
    setattr(m, k, v)
  return m

re_json = re.compile(r"^application/json", re.IGNORECASE)

# Parse the body of an upload based on the type if you are trying to post a cgi.FieldStorage object
# you should instead upload those blob seperately via the special /api/files url.
def parse_body(self):
  if re_json.match(self.request.content_type):
    data = json.loads(self.request.body)
  else:
    data = {}
    for k,v in self.request.POST.items():
      if isinstance(v, cgi.FieldStorage):
        raise AppError("Files should be uploaded seperately as their own form to /api/files/ and \
            then their ids should be uploaded and stored with the object.")
      if data.has_key(k):
        current = data[k]
        if isinstance(current, list):
          current.append(v)
        else:
          data[k] = [current,v]
      else:
        data[k] = v
  return data or {}

# Strips any disallowed names {id, _*, etc}.
def clean_data(data):
  disallowed_names = ["Id", "id", "key"]
  disallowed_prefixes = ["_", "$"]
  exceptions = ["Id"]
  for key in data.keys():
    if key[0] in disallowed_prefixes or key in disallowed_names:
      if key not in exceptions:
        logging.warn("Disallowed key {%s} passed in object creation." % key)
      del data[key]
  return data

# Parse the id either given or extracted from the data.
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

# Convert a value to its inferred python type. Note all numbers are stored as floats which by cause
# percision issues in odd cases.
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

# Construct an ndb filter from the query args. Example:
#
#    www.myurl.com?filter=name==other&filter=size<=5
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

# Construct an ndb order from the query args.
def construct_order(cls, o):
  neg = True if o[0] == "-" else False
  o = o[1:] if neg else o
  if hasattr(cls, o):
    p = getattr(cls, o)
  else:
    p = ndb.GenericProperty(o)
  return -p if neg else p

# Construct the filter from a json object.
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

# Construct a query from a json object which includes the filter and order parameters
def construct_query_from_json(cls, filters, orders):
  q = cls.query()
  if filters:
    q = q.filter(construct_filter_json(filters))
  if orders:
    q = q.order(*[construct_order(cls,o) for o in orders])
  return q

# Construct a query from url args
def construct_query_from_url_args(cls, filters, orders):
  q = cls.query()
  q = q.filter(*[construct_filter(f) for f in filters])
  # TODO(doug) correctly auto append orders when necessary like on a multiselect/OR
  q = q.order(*[construct_order(cls,o) for oo in orders for o in re_split.split(oo)])
  return q

# Determine which kind of query parameters are passed in and construct the query.
# Includes paginated results in the response Headers for "More", "Next-Cursor", and "Prev-Cursor"
def query(self, cls):
  params = self.request.get("params")
  if params:
    params = json.loads(params)
    page_size = params.get("page_size", 100)
    cursor = params.get("cursor")
    filters = params.get("filter")
    orders = params.get("order")
    projection = params.get("projection") or None
    q = construct_query_from_json(cls, filters, orders)
  else:
    page_size = int(self.request.get("page_size", default_value=100))
    cursor = self.request.get("cursor")
    projection = self.request.get("projection")
    projection = projection.split(",") if projection else None
    filters = self.request.get_all("filter")
    orders = self.request.get_all("order")
    q = construct_query_from_url_args(cls, filters, orders)
  cursor = Cursor.from_websafe_string(cursor) if cursor else None

  results, cursor, more = q.fetch_page(page_size=page_size, cursor=cursor, projection=projection)
  self.response.headers["More"] = "true" if more else "false"
  if cursor:
    self.response.headers["Next-Cursor"] = cursor.urlsafe()
    self.response.headers["Prev-Cursor"] = cursor.reversed().urlsafe()
  return [m.to_dict() for m in results]

# This does all the simple restful handling that you would expect. There is a special catch for
# /users/me which will look up your logged in id and return your information.
class RestfulHandler(BaseHandler):
  @as_json
  def get(self, model, id):
    # TODO(doug) does the model name need to be ascii encoded since types don't support utf-8?
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
          u = api.users.get_current_user()
          m.email = u.email()
          m.key = ndb.Key("users", id)
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
      if old_model and not old_model.is_owner(u):
        raise AppError("You do not have sufficient privileges.")
    m = reflective_create(cls, data)
    if id:
      m.key = ndb.Key(model, id)
    if model != "users":
      if len(m.owners) == 0:
        m.owners.append(u)
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

class AdminHandler(BaseHandler):
  """Admin routes"""
  @as_json
  def get(self, action):
    if not api.users.is_current_user_admin():
      raise LoginError("You must be an admin.")
    def notFound(self):
      self.error(404)
      return {"error": "Not Found"}
    return {
    }.get(action, notFound)(self)

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

class FilesHandler(blobstore_handlers.BlobstoreDownloadHandler):
  @as_json
  def get(self, key):
    if key == "":
      current_user(required=True)
      return {
          "upload_url": blobstore.create_upload_url("/api/files/upload")
          }
    key = str(urllib.unquote(key))
    blob_info = blobstore.BlobInfo.get(key)
    if blob_info:
      self.send_blob(blob_info)
      raise BreakError
    else:
      self.error(404)
      return {"error": "File not found with key " + key}

  @as_json
  def post(self, _):
    raise AppError("You must make a GET call to /api/files to get a POST url.")

  @as_json
  def put(self, _):
    raise AppError("PUT is not supported for the files api.")

  @as_json
  def delete(self, key):
    current_user(required=True)
    key = blobstore.BlobKey(str(urllib.unquote(key)))
    blob_info = blobstore.BlobInfo.get(key)
    if blob_info:
      blob_info.delete()
      if re_image.match(blob_info.content_type):
        delete_serving_url(key)
      return {}
    else:
      self.error(404)
      return {"error": "File not found with key " + key}

class FilesUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
  @as_json
  def post(self):
    return [blob_info_to_dict(b) for b in self.get_uploads()]


# converting numbers to strings so that the user id is represented more consistently
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


# Fetch the current user id or None
def current_user(required=False):
  u = api.users.get_current_user()
  if u:
    return convert_num_to_str(u.user_id())
  if required:
    raise LoginError("User must be logged in.")
  return None


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

# Simple Proxy Server
# ---------------------
#
# Simple proxy server should you need it. Comment out the code in app.yaml to enable.
#
class ProxyHandler(webapp2.RequestHandler):
  def proxy(self, *args, **kwargs):
    url = urllib.unquote(self.request.get('url'))
    if url:
      resp = urlfetch.fetch(url, method=self.request.method, headers=self.request.headers)
      for k,v in resp.headers.iteritems():
        self.response.headers[k] = v
      self.response.status = resp.status_code
      self.response.out.write(resp.content)
    else:
      self.response.out.write("Must provide a 'url' parameter.")
  def get(self, *args, **kwargs):
    self.proxy(*args, **kwargs)
  def put(self, *args, **kwargs):
    self.proxy(*args, **kwargs)
  def post(self, *args, **kwargs):
    self.proxy(*args, **kwargs)
  def delete(self, *args, **kwargs):
    self.proxy(*args, **kwargs)

# Test Handler
# ------------
#
# QUnit tests can only be preformed on the local host because they actively modify the database and
# don't properly clean up after themselves yet.
class TestHandler(webapp2.RequestHandler):
  def get(self):
    if DEBUG:
      with open('tailbone/test_tailbone.html') as f:
        self.response.out.write(f.read())
    else:
      self.response.out.write("Sorry, tests can only be run from localhost because they modify the \
      datastore.")

# Some Extra HTML handlers
# ------------------------
class LoginPopupHandler(webapp2.RequestHandler):
  def get(self):
    u = current_user()
    if u:
      m = users.get_by_id(u)
      if not m:
        m = users(key=ndb.Key('users', u))
      msg = m.to_dict()
    else:
      msg = None
    self.response.out.write("""
<!doctype html>
<html>
<head>
  <title></title>
</head>
<body>
If this window does not close, please click <a id="origin">here</a> to refresh.
<script type="text/javascript">
  var targetOrigin = window.location.origin || ( window.location.protocol + "//" + window.location.host );
  document.querySelector("#origin").href = targetOrigin;
  window.opener.postMessage({}, targetOrigin);
  window.close();
</script>
</body>
</html>
""".format({"type":"Login", "payload": msg}))

PREFIX = "/api/"

NAMESPACE = os.environ.get("NAMESPACE", "")
DEBUG = os.environ.get("SERVER_SOFTWARE", "").startswith("Dev")

app = webapp2.WSGIApplication([
  (r"{}login".format(PREFIX), LoginHandler),
  (r"{}login.html".format(PREFIX), LoginPopupHandler),
  (r"{}logout" .format(PREFIX), LogoutHandler),
  (r"{}test" .format(PREFIX), TestHandler),
  (r"{}admin/(.+)".format(PREFIX), AdminHandler),
  (r"{}files/upload".format(PREFIX), FilesUploadHandler),
  (r"{}files/?(.*)".format(PREFIX), FilesHandler),
  (r"{}events/.*".format(PREFIX), EventsHandler),
  (r"{}([^/]+)/?(.*)".format(PREFIX), RestfulHandler),
  ], debug=DEBUG)

connected = webapp2.WSGIApplication([
  ("/_ah/channel/connected/", ConnectedHandler),
  ("/_ah/channel/disconnected/", DisconnectedHandler),
  ], debug=DEBUG)

proxy = webapp2.WSGIApplication([
  (r"/proxy", ProxyHandler),
  ], debug=DEBUG)

