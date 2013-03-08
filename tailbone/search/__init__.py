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
    idx = search.Index(name=index_name)
    fields = []
    for k, v in m.iteritems():
      # skip things starting with _ like _index
      if k[0] == "_":
        continue
      cls = getattr(search, v)
      fields.append(cls(name=k, value=getattr(model, k)))
    logging.error(fields)
    logging.error(model.key.urlsafe())
    doc = search.Document(doc_id=model.key.urlsafe(), fields=fields)
    try:
      idx.put(doc)
    except search.Error:
      logging.error("Failed to put document {}".format(doc))

def delete(key):
  if _searchable:
    kind = key.kind()
    m = _searchable.get(kind)
    if not m:
      return
    index_name = m.get("_index", _INDEX_NAME)
    idx = search.Index(name=index_name)
    idx.delete(key.urlsafe())

class SearchHandler(BaseHandler):
  @as_json
  def get(self, index_name):
    index_name = index_name or _INDEX_NAME
    q = self.request.get("q")
    if q:
      q = json.loads(q)
    return {}

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
    _SEARCHABLE = compile_searchable(json.load(f))
except ValueError:
  logging.error("searchable.json is not a valid json document.")
except IOError:
  logging.info("searchable.json doesn't exist nothing can be searched.")

app = webapp2.WSGIApplication([
  (r"{}search/?(.*)".format(PREFIX), SearchHandler),
  ], debug=DEBUG)


