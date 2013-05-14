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
from tailbone import AppError, LoginError, BreakError, as_json, parse_body, BaseHandler, DEBUG, PREFIX
from tailbone import search
from counter import get_count, increment, decrement

import datetime
import json
import logging
import os
import re
import webapp2

from google.appengine import api
from google.appengine.ext import ndb


re_public = re.compile(r"^[A-Z].*")
re_type = type(re_public)

acl_attributes = [u"owners", u"viewers"]

store_metadata = os.environ.get("METADATA","true") == "true"


def current_user(required=False):
  u = webapp2.get_request().environ.get("TAILBONE_USER_ID")
  if u:
    return ndb.Key("users", u).urlsafe()
  if required:
    raise LoginError("User must be logged in.")
  return None


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
    result["Id"] = self.key.urlsafe()
    return result

  @classmethod
  def _pre_delete_hook(cls, key):
    m = key.get()
    u = current_user(required=True)
    if not m.can_write(u):
      raise AppError("You ({}) do not have permission to delete this model ({}).".format(u, key.id()))


# User
# ----
# User is an special model that can only be written to by the google account owner.
class users(ndb.Expando):
  def to_dict(self, *args, **kwargs):
    result = super(users, self).to_dict(*args, **kwargs)
    u = current_user()
    if u and u == self.key.urlsafe():
      pass
    else:
      for k in result.keys():
        if not re_public.match(k):
          del result[k]
    result["Id"] = self.key.urlsafe()
    return result


# Reflectively instantiate a class given some data parsed by the restful json POST. If the size of
# an object is larger than 500 characters it cannot be indexed. Otherwise everything else is. In the
# future there may be a way to express what should be indexed or searchable, but not yet.
_latlon = set(["lat", "lon"])
_reISO = re.compile("^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}(?:\.\d*)?)Z$")
_reKey = re.compile("^[a-zA-Z0-9\-]{10,500}$")


def reflective_create(cls, data):
  m = cls()
  for k, v in data.iteritems():
    m._default_indexed = True
    t = type(v)
    if t in [unicode, str]:
      if len(bytearray(v, encoding="utf8")) >= 500:
        m._default_indexed = False
      elif _reISO.match(v):
        try:
          values = map(int, re.split('[^\d]', v)[:-1])
          values[-1] *= 1000  # to account for python using microseconds vs js milliseconds
          v = datetime.datetime(*values)
        except ValueError as e:
          # logging.info("{} key:'{}' value:{}".format(e, k, v))
          pass
      elif _reKey.match(v):
        try:
          v = ndb.Key(urlsafe=v)
        except Exception as e:
          # logging.info("{} key:'{}' value:{}".format(e, k, v))
          pass
    elif t == dict:
      recurse = True
      if set(v.keys()) == _latlon:
        try:
          v = ndb.GeoPt(v["lat"], v["lon"])
          recurse = False
        except api.datastore_errors.BadValueError as e:
          logging.info("{} key:'{}' value:{}".format(e, k, v))
          pass
      if recurse:
        subcls = unicode.encode(k, "ascii", errors="ignore")
        v = reflective_create(type(subcls, (ndb.Expando,), {}), v)
    elif t == float:
      v = float(v)
    elif t == int:  # currently all numbers are floats for purpose of quering TODO find better solution
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
def parse_id(id, model, data_id=None):
  if data_id:
    if id:
      if data_id != id:
        raise AppError("Url id {%s} must match object id {%s}" % (id, data_id))
    else:
      id = data_id
  if id:
    key = ndb.Key(urlsafe=id)
    if model != key.kind():
      raise AppError("Key kind must match id kind: {} != {}.".format(model, key.kind()))
    return key
  return None

re_filter = re.compile(r"^([\w\-.]+)(!=|==|=|<=|>=|<|>)(.+)$")
re_composite_filter = re.compile(r"^(AND|OR)\((.*)\)$")
re_split = re.compile(r",\W*")


def convert_value(value):
  if value == "true":
    value = True
  elif value == "false":
    value = False
  elif _reKey.match(value):
    try:
      value = ndb.Key(urlsafe=value)
    except TypeError:
      pass
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
      filters = [construct_filter_json(x) for x in f[1:]]
      return ndb.query.AND(*filters)
    elif f[0] == "OR":
      filters = [construct_filter_json(x) for x in f[1:]]
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
    q = q.order(*[construct_order(cls, o) for o in orders])
  return q


# Construct a query from url args
def construct_query_from_url_args(cls, filters, orders):
  q = cls.query()
  q = q.filter(*[construct_filter(f) for f in filters])
  # TODO(doug) correctly auto append orders when necessary like on a multiselect/OR
  q = q.order(*[construct_order(cls, o) for oo in orders for o in re_split.split(oo)])
  return q


# Determine which kind of query parameters are passed in and construct the query.
# Includes paginated results in the response Headers for "More", "Next-Cursor", and "Reverse-Cursor"
def query(self, cls, *extra_filters):
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
    projection = self.request.get_all("projection")
    projection = [i for sublist in projection for i in sublist.split(",")] if projection else None
    filters = self.request.get_all("filter")
    orders = self.request.get_all("order")
    q = construct_query_from_url_args(cls, filters, orders)
  for f in extra_filters:
    q = f(q)
  cursor = ndb.Cursor.from_websafe_string(cursor) if cursor else None
  if projection:
    # if asking for private variables and not specifing owners and viewers append them
    private = [p for p in projection if not re_public.match(p)]
    if len(private) > 0:
      acl = [p for p in private if p in acl_attributes]
      if len(acl) == 0:
        raise AppError("Requesting projection of private properties, but did not specify 'owners' or 'viewers' to verify access.")
  results, cursor, more = q.fetch_page(page_size, start_cursor=cursor, projection=projection)
  self.response.headers["More"] = "true" if more else "false"
  if cursor:
    self.response.headers["Cursor"] = cursor.urlsafe()
    # The Reverse-Cursor is used if you construct a query in the opposite direction
    self.response.headers["Reverse-Cursor"] = cursor.reversed().urlsafe()
  return [m.to_dict() for m in results]


# Helper function to validate the date recursively if needed.
def _validate(validator, data, ignored=None):
  if isinstance(validator, re_type):
    if validator.pattern == "":
      return
    if type(data) not in [str, unicode]:
      data = json.dumps(data)
    if not validator.match(data):
      raise AppError("Validator '{}' does not match '{}'".format(validator.pattern, data))
  elif isinstance(validator, dict) and isinstance(data, dict):
    for name, val in data.iteritems():
      if name not in ignored:
        _validate(validator.get(name), val)
  else:
    raise AppError("Unsupported validator type {} : {}".format(validator, type(validator)))


# This validates the data see validation.template.json for an example.
# Must create a validation.json in the root of your application.
def validate(cls_name, data):
  # properties = data.keys()
  # confirm the format of any tailbone specific types
  for name in acl_attributes:
    val = data.get(name)
    if val:
      # TODO(doug): validate list, can't be empty list, must contain id like objects
      pass
  # run validation over remaining properties
  if _validation:
    validations = _validation.get(cls_name)
    if not validations:
      raise AppError("Validation requires all valid models to be listed, use empty quote to skip.")
    _validate(validations, data, acl_attributes)


# This does all the simple restful handling that you would expect. There is a special catch for
# /users/me which will look up your logged in id and return your information.
class RestfulHandler(BaseHandler):
  def _get(self, model, id, *extra_filters):
    # TODO(doug) does the model name need to be ascii encoded since types don't support utf-8?
    cls = users if model == "users" else type(model.lower(), (ScopedExpando,), {})
    if id:
      me = False
      if model == "users":
        if id == "me":
          me = True
          id = current_user(required=True)
      key = parse_id(id, model)
      m = key.get()
      if not m:
        if model == "users" and me:
          m = users()
          m.key = key
          setattr(m, "$unsaved", True)
          environ = webapp2.get_request().environ
          for k, v in environ.iteritems():
            if k[:14] == "TAILBONE_USER_" and k != "TAILBONE_USER_ID" and v:
              setattr(m, k[14:].lower(), v)
        else:
          raise AppError("No {} with id {}.".format(model, id))
      return m.to_dict()
    else:
      return query(self, cls, *extra_filters)

  def _delete(self, model, id):
    if not id:
      raise AppError("Must provide an id.")
    model = model.lower()
    u = current_user(required=True)
    if model == "users":
      if id != "me" and id != u:
        raise AppError("Id must be the current " +
                       "user_id or me. User {} tried to modify user {}.".format(u, id))
      id = u
    key = parse_id(id, model)
    key.delete()
    search.delete(key)
    if store_metadata:
      decrement(model)
    return {}

  def set_or_create(self, model, id, parent_key=None):
    u = current_user(required=True)
    if model == "users":
      if not (id == "me" or id == "" or id == u):
        raise AppError("Id must be the current " +
                       "user_id or me. User {} tried to modify user {}.".format(u, id))
      id = u
      cls = users
    else:
      cls = type(model.lower(), (ScopedExpando,), {})
    data = parse_body(self)
    key = parse_id(id, model, data.get("Id"))
    clean_data(data)
    validate(cls.__name__, data)
    already_exists = False
    if key:
      old_model = key.get()
      if old_model:
        if model != "users" and not old_model.can_write(u):
          raise AppError("You do not have sufficient privileges.")
        already_exists = True

    # TODO: might want to add this post creation since you already have the key
    if parent_key:
      data[parent_key.kind()] = parent_key.urlsafe()

    m = reflective_create(cls, data)
    if key:
      m.key = key
    if model != "users":
      if len(m.owners) == 0:
        m.owners.append(u)
    m.put()
    # increment count
    if not already_exists and store_metadata:
      increment(model)
    # update indexes
    search.put(m)
    redirect = self.request.get("redirect")
    if redirect:
      self.redirect(redirect)
      # Raising break error to avoid header and body writes from @as_json decorator since we override as a redirect
      raise BreakError()
    return m.to_dict()

  # Metadata including the count in the response header
  def head(self, model, id):
    if store_metadata:
      model = model.lower()
      metadata = {
        "total": get_count(model)
      }
      self.response.headers["Metadata"] = json.dumps(metadata)

  @as_json
  def get(self, model, id):
    return self._get(model, id)

  @as_json
  def post(self, *args):
    return self.set_or_create(*args)

  @as_json
  def patch(self, *args):
    # TODO: implement this differently to do partial update
    return self.set_or_create(*args)

  @as_json
  def put(self, *args):
    return self.set_or_create(*args)

  @as_json
  def delete(self, *args):
    return self._delete(*args)


class NestedRestfulHandler(RestfulHandler):
  def get_parent(parent_model, parent_id):
    parent_key = ndb.Key(parent_model, parent_id)
    parent = parent_key.get()
    if not parent:
      raise AppError("Parent model {}:{} does not exists.".format(parent_model, parent_id))
    return parent

  @as_json
  def get(self, parent_model, parent_id, model, id):
    parent = self.get_parent(parent_model, parent_id)
    parent_key = parent.key

    def belongs_to_filter(q):
      cls = type(parent_model.lower(), (ScopedExpando,), {})
      field = getattr(cls, parent_model)
      return q.filter(field == parent_key)
    return self._get(model, id, belongs_to_filter)

  def set_or_create(self, parent_model, parent_id, model, id):
    parent = self.get_parent(parent_model, parent_id)
    s = super(NestedRestfulHandler, self)
    s.set_or_create(model, id, parent.key)

  def _delete(self, parent_model, parent_id, model, id):
    self.get_parent(parent_model, parent_id)
    return super(NestedRestfulHandler, self)._delete(model, id)


# Load an optional validation.json
# --------------------------------
def compile_validation(target):
  if not isinstance(target, dict):
    logging.error("validation.json invalid, target is {}".format(target))
    raise ValueError("Invalid target type")
  for k, v in target.iteritems():
    if type(v) in [str, unicode]:
      target[k] = re.compile(v)
    else:
      target[k] = compile_validation(v)
  return target

_validation = None
try:
  with open("validation.json") as f:
    _validation = compile_validation(json.load(f))
except ValueError:
  logging.error("validation.json is not a valid json document.")
except IOError:
  logging.info("validation.json doesn't exist no model validation will be performed.")

app = webapp2.WSGIApplication([
  (r"{}([^/]+)/([^/]+)/([^/]+)/?(.*)".format(PREFIX), NestedRestfulHandler),
  (r"{}([^/]+)/?(.*)".format(PREFIX), RestfulHandler),
], debug=DEBUG)
