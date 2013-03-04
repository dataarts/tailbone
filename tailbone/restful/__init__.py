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

# shared resources and global variables
from tailbone import *

import datetime
import json
import logging
import os
import re
import sys
import time
import urllib
import webapp2
import yaml

from google.appengine import api
from google.appengine.ext import deferred
from google.appengine.ext import ndb


re_public = re.compile(r"^[A-Z].*")

# Model
# -----
# A modifed Expando class that all models derive from, this allows app engine to work as an
# arbitrary document store for your json objects as well as scope the public private nature of
# objects based on the capitolization of the property.
class ScopedExpando(ndb.Expando):
  owners = ndb.StringProperty(repeated=True)
  viewers = ndb.StringProperty(repeated=True)

  def can_write(self, u):
    try:
      owners = self.owners
    except ndb.UnprojectedPropertyError:
      owners = []
    if u and u in owners:
      return True
    return False

  def can_read(self, u):
    try:
      owners = self.owners
    except ndb.UnprojectedPropertyError:
      owners = []
    try:
      viewers = self.viewers
    except ndb.UnprojectedPropertyError:
      viewers = []
    if u and (u in owners or u in viewers):
      return True
    return False


  def to_dict(self, *args, **kwargs):
    result = super(ScopedExpando, self).to_dict(*args, **kwargs)
    if not self.can_read(current_user()):
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
    # try:
    #   value = int(value)
    # except:
    #   try:
    #     value = float(value)
    #   except:
    #     pass
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
# Includes paginated results in the response Headers for "More", "Next-Cursor", and "Reverse-Cursor"
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
  cursor = ndb.Cursor.from_websafe_string(cursor) if cursor else None
  if projection:
    # if asking for private variables and not specifing owners and viewers append them
    private = [p for p in projection if not re_public.match(p)]
    if len(private) > 0:
      acl = [p for p in private if p == "owners" or p == "viewers"]
      if len(acl) == 0:
        projection += ["owners", "viewers"]
  results, cursor, more = q.fetch_page(page_size, start_cursor=cursor, projection=projection)
  self.response.headers["More"] = "true" if more else "false"
  if cursor:
    self.response.headers["Cursor"] = cursor.urlsafe()
    # The Reverse-Cursor is used if you construct a query in the opposite direction
    self.response.headers["Reverse-Cursor"] = cursor.reversed().urlsafe()
  return [m.to_dict() for m in results]

# This does all the simple restful handling that you would expect. There is a special catch for
# /users/me which will look up your logged in id and return your information.
class RestfulHandler(BaseHandler):
  @as_json
  def get(self, model, id):
    # TODO(doug) does the model name need to be ascii encoded since types don't support utf-8?
    cls = users if model == "users" else type(model.lower(), (ScopedExpando,), {})
    if id:
      me = False
      if model == "users":
        if id == "me":
          me = True
          id = current_user(required=True)
      id = parse_id(id)
      m = cls.get_by_id(id)
      if not m:
        if model == "users" and me:
          u = api.users.get_current_user()
          m = users()
          m.email = u.email()
          m.key = ndb.Key("users", id)
          setattr(m, "$unsaved", True)
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
      if old_model and not old_model.can_write(u):
        raise AppError("You do not have sufficient privileges.")
    m = reflective_create(cls, data)
    if id:
      m.key = ndb.Key(model, id)
    if model != "users":
      if len(m.owners) == 0:
        m.owners.append(u)
    m.put()
    redirect = self.request.get("redirect")
    if redirect:
      self.redirect(redirect)
      raise BreakError()
      return
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


# Test Handler
# ------------
#
# QUnit tests can only be preformed on the local host because they actively modify the database and
# don't properly clean up after themselves yet.
class TestHandler(webapp2.RequestHandler):
  def get(self):
    if DEBUG:
      with open('tailbone/restful/test_restful.html') as f:
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

# Load an optional validation.json
# --------------------------------
validation = None
try:
  with open("validation.json") as f:
    validation = json.load(f)
    models = validation.get("models")
    if models:
      for model, props in models.iteritems():
        for prop, value in props.iteritems():
          props[prop] = re.compile(value)
    else:
      validation = None
      logging.error("validation.json present but no models specified.")
except ValueError:
  logging.error("validation.json is not a valid json document.")
except IOError:
  logging.info("validation.json doesn't exist no model validation will be preformed.")

app = webapp2.WSGIApplication([
  (r"{}login".format(PREFIX), LoginHandler),
  (r"{}login.html".format(PREFIX), LoginPopupHandler),
  (r"{}logout" .format(PREFIX), LogoutHandler),
  (r"{}test" .format(PREFIX), TestHandler),
  (r"{}([^/]+)/?(.*)".format(PREFIX), RestfulHandler),
  ], debug=DEBUG)


