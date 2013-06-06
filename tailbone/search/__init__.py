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

from google.appengine.api import search
from google.appengine.ext import deferred
from google.appengine.ext import ndb

_INDEX_NAME = "default"

def put(model):
  if _searchable:
    kind = model.key.kind()
    m = _searchable.get(kind)
    if not m:
      return
    index_name = m.get("_index", _INDEX_NAME)
    index = search.Index(name=index_name)
    fields = []
    for k, v in m.iteritems():
      # skip things starting with _ like _index
      if k[0] == "_":
        continue
      cls = getattr(search, v)
      search_val = getattr(model, k, None)
      if not search_val:
        continue
      # Note: GeoPt values should be converted tp search.GeoPoint values before adding to the search index !
      if isinstance(search_val, ndb.GeoPt):
         search_val = search.GeoPoint(search_val.lat, search_val.lon)
      fields.append(cls(name=k, value=search_val))
    # add a Kind type to all searchable items in the default index
    if index_name == _INDEX_NAME:
      fields.append(search.TextField(name="Kind", value=kind))
    doc = search.Document(doc_id=model.key.urlsafe(), fields=fields)
    try:
      index.put(doc)
    except search.Error:
      logging.error("Failed to put document {}".format(doc))

def delete(key):
  if _searchable:
    kind = key.kind()
    m = _searchable.get(kind)
    if not m:
      return
    index_name = m.get("_index", _INDEX_NAME)
    index = search.Index(name=index_name)
    try:
      index.delete(key.urlsafe())
    except search.DeleteError as e:
      logging.error("Failed to delete document {}: {}".format(key, e))


def doc_to_json(doc):
  d = {}
  key = ndb.Key(urlsafe=doc.doc_id)
  d["Id"] = key.id()
  for f in doc.fields:
    if f.name[0].isupper():
      d[f.name] = f.value
  return d

class SearchHandler(BaseHandler):
  @as_json
  def get(self, index_name):
    q = self.request.get("q", "")
    limit = self.request.get_range("limit", default=100)
    cursor = self.request.get("cursor", None)
    if cursor:
      cursor = search.Cursor(web_safe_string=cursor)
    # TODO(doug): some way to express sort calculations
    # sort = parse_sort(self.request.get_all("sort"))
    sort = None
    returned_fields = self.request.get("returned_fields", None)
    if returned_fields:
      try:
        returned_fields = json.loads(returned_fields)
      except ValueError:
        returned_fields = None
    snippeted_fields = self.request.get("snippeted_fields", None)
    if snippeted_fields:
      try:
        snippeted_fields = json.loads(snippeted_fields)
      except ValueError:
        snippeted_fields = None
    options = search.QueryOptions(
                limit=limit,  # the number of results to return
                cursor=cursor,
                sort_options=sort,
                returned_fields=returned_fields,
                snippeted_fields=snippeted_fields)
    query = search.Query(query_string=q, options=options)

    index_name = index_name or _INDEX_NAME
    index = search.Index(name=index_name)
    try:
      results = index.search(query)
    except search.Error as e:
      raise AppError("Search Error: {}".format(e))
    return [doc_to_json(d) for d in results]

# Load an optional searchable.json
# --------------------------------
def compile_searchable(target):
  if not isinstance(target, dict):
    logging.error("searchable.json invalid, target is {}".format(target))
    raise ValueError("Invalid target type")
  for k, v in target.iteritems():
    if type(v) not in [str, unicode]:
      target[k] = compile_searchable(v)
  return target

_searchable = None
try:
  with open("searchable.json") as f:
    _searchable = compile_searchable(json.load(f))
except ValueError:
  logging.error("searchable.json is not a valid json document.")
except IOError:
  logging.info("searchable.json doesn't exist nothing can be searched.")

app = webapp2.WSGIApplication([
  (r"{}search/?(.*)".format(PREFIX), SearchHandler),
  ], debug=DEBUG)


