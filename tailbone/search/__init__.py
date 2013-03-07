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

_INDEX_NAME = "default"

class SearchHandler(BaseHandler):
  @as_json
  def get(self, index_name):
    index_name = index_name or _INDEX_NAME
    q = self.request.get("q")
    if q:
      q = json.loads(q)
    return {}

_indexes = {}
# Load an optional searchable.json
# --------------------------------
def compile_searchable(target):
  if not isinstance(target, dict):
    logging.error("searchable.json invalid, target is {}".format(target))
    raise ValueError("Invalid target type")
  for k, v in target.iteritems():
    if type(v) in [str, unicode]:
      target[k] = re.compile(v)
    else:
      target[k] = compile_validation(v)
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


