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

import cgi
import functools
import json
import logging
import os
import re
import string
import time
import webapp2

from google.appengine import api
from google.appengine.ext import ndb
from google.appengine.ext import testbed

PREFIX = "/api/"
NAMESPACE = os.environ.get("NAMESPACE", "")
DEBUG = os.environ.get("SERVER_SOFTWARE", "").startswith("Dev")


# Custom Exceptions
class AppError(Exception):
  pass


class BreakError(Exception):
  pass


class LoginError(Exception):
  pass


# Extensions to the jsonifying of python results
def json_extras(obj):
  """Extended json processing of types."""
  if hasattr(obj, "get_result"):  # RPC
    return obj.get_result()
  if hasattr(obj, "strftime"):  # datetime
    return obj.strftime("%Y-%m-%dT%H:%M:%S.") + str(obj.microsecond / 1000) + "Z"
  if isinstance(obj, ndb.GeoPt):
    return {"lat": obj.lat, "lon": obj.lon}
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
      if not resp:
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
      resp = {"error": e.__class__.__name__, "message": e.message}
      if api.app_identity.get_application_id() != testbed.DEFAULT_APP_ID:
        logging.error(str(e))
    if not isinstance(resp, str) and not isinstance(resp, unicode):
      resp = json.dumps(resp, default=json_extras)
    # # UNCOMMENT TO ENABLE JSONP
    # callback = self.request.get("callback")
    # if callback:
    #   self.response.headers["Content-Type"] = "text/javascript"
    #   resp = "%s(%s);" % (_callback, resp)
    self.response.out.write(resp)
  return wrapper


# BaseHandler for error handling
class BaseHandler(webapp2.RequestHandler):
  def handle_exception(self, exception, debug):
    # Log the error.
    logging.error(exception)

    # If the exception is a HTTPException, use its error code.
    # Otherwise use a generic 500 error code.
    if isinstance(exception, webapp2.HTTPException):
      self.response.set_status(exception.code)
    else:
      self.response.set_status(500)

    return {"error": str(exception)}

re_json = re.compile(r"^application/json", re.IGNORECASE)


# Parse the body of an upload based on the type if you are trying to post a cgi.FieldStorage object
# you should instead upload those blob separately via the special /api/files url.
def parse_body(self):
  if re_json.match(self.request.content_type):
    data = json.loads(self.request.body)
  else:
    data = {}
    for k, v in self.request.POST.items():
      if isinstance(v, cgi.FieldStorage):
        raise AppError("Files should be uploaded separately as their own form to /api/files/ and \
            then their ids should be uploaded and stored with the object.")
      if type(v) in [str, unicode]:
        try:
          v = json.loads(v)
        except ValueError:
          pass
      # TODO(doug): Bug when loading multiple json lists with same key
      # TODO(doug): Bug when loading a number that should be a string representation of said number
      if k in data:
        current = data[k]
        if isinstance(current, list):
          current.append(v)
        else:
          data[k] = [current, v]
      else:
        data[k] = v
  return data or {}


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


class LoginHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect(
        api.users.create_login_url(
          self.request.get("continue", default_value="/")))


class LogoutHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect(
        api.users.create_logout_url(
          self.request.get("continue", default_value="/")))


auth = webapp2.WSGIApplication([
  (r"{}login".format(PREFIX), LoginHandler),
  (r"{}logout" .format(PREFIX), LogoutHandler),
], debug=DEBUG)
