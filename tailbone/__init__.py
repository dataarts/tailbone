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
import sys
try:
  import traceback
except:
  pass
import webapp2
import yaml

from google.appengine import api
from google.appengine.ext import ndb

sys.path.insert(0, "tailbone/dependencies.zip")
from oauth2client.appengine import AppAssertionCredentials
import httplib2
from apiclient.discovery import build

PREFIX = "/api/"
DEBUG = os.environ.get("SERVER_SOFTWARE", "").startswith("Dev")

PROTECTED = [re.compile("(mesh|messages|files|events|admin|proxy)", re.IGNORECASE), re.compile("tailbone.*", re.IGNORECASE)]


class _ConfigDefaults(object):
  JSONP = False
  SERVICE_EMAIL = None
  SERVICE_KEY_PATH = None
  CORS = False
  CORS_RESTRICTED_DOMAINS = None
  CONFIG = {}

  def is_current_user_admin(*args, **kwargs):
    return api.users.is_current_user_admin(*args, **kwargs)

  def get_current_user(*args, **kwargs):
    return api.users.get_current_user(*args, **kwargs)

  def create_login_url(*args, **kwargs):
    return api.users.create_login_url(*args, **kwargs)

  def create_logout_url(*args, **kwargs):
    return api.users.create_logout_url(*args, **kwargs)

  # This is handled by app engine use this if you have some external setup
  def login_hook(*args, **kwargs):
    return None

  def logout_hook(*args, **kwargs):
    return None

config = api.lib_config.register('tailbone', _ConfigDefaults.__dict__)


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
  if hasattr(obj, "strftime"):  # datetime or date
    #return obj.strftime("%Y-%m-%dT%H:%M:%S.") + str(obj.microsecond / 1000) + "Z"
    return obj.isoformat()
  if isinstance(obj, ndb.GeoPt):
    return {"lat": obj.lat, "lon": obj.lon}
  if isinstance(obj, ndb.Key):
    r = webapp2.get_request()
    if r.get("recurse", default_value=False): 
      item = obj.get()
      current_level = [key for key in recurse_class.keys() if obj.kind() in recurse_class[key]] or 1
      current_level = current_level[0] if current_level != 1 else 1
      if current_level > recurse_depth:
        return obj.urlsafe()
      if item is None:
        return obj.urlsafe()
      item = item.to_dict()
      item["Id"] = obj.urlsafe()
      item["$class"] = obj.kind()
      recurse_class[current_level].add(item["$class"])
      for key in item.keys():
        if isinstance(item[key], ndb.Key) or (type(item[key]) == list and len(item[key]) > 0 and isinstance(item[key][0], ndb.Key)):
          child_class = item[key].kind() if isinstance(item[key], ndb.Key) else item[key][0].kind()
          if not current_level+1 in recurse_class.keys():
            recurse_class.update({current_level+1: set()})
          recurse_class[current_level+1].add(child_class)
      return item
    return obj.urlsafe()
  return None


# Decorator to return the result of a function as json. It supports jsonp by default.
def as_json(func):
  """Returns json when callback in url"""
  @functools.wraps(func)
  def wrapper(self, *args, **kwargs):
    global recurse_excute, recurse_depth
    recurse_depth = int(self.request.get("depth", default_value=2))
    recurse_class = {1: set()}
    self.response.headers["Content-Type"] = "application/json"
    if DEBUG:
      self.response.headers["Access-Control-Allow-Origin"] = "*"
      self.response.headers["Access-Control-Allow-Methods"] = "POST,GET,PUT,PATCH,HEAD,OPTIONS"
      self.response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    try:
      resp = func(self, *args, **kwargs)
      if resp is None:
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
    except (AppError, api.datastore_errors.BadArgumentError,
            api.datastore_errors.BadRequestError) as e:
      self.response.set_status(400)
      resp = {"error": e.__class__.__name__, "message": e.message}
    if not isinstance(resp, str) and not isinstance(resp, unicode):
      resp = json.dumps(resp, default=json_extras)
    if config.JSONP:
      callback = self.request.get("callback")
      if callback:
        self.response.headers["Content-Type"] = "text/javascript"
        resp = "%s(%s);".format(callback, resp)
    if config.CORS:
      origin = self.request.headers.get("Origin")
      if not config.CORS_RESTRICTED_DOMAINS:
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
      elif origin in config.CORS_RESTRICTED_DOMAINS:
        self.response.headers.add_header("Access-Control-Allow-Origin", origin)
    self.response.out.write(resp)
  return wrapper


# BaseHandler for error handling
class BaseHandler(webapp2.RequestHandler):
  def handle_exception(self, exception, debug):
    # Log the error.
    logging.error(exception)
    if traceback:
      logging.error(traceback.format_exc())

    # If the exception is a HTTPException, use its error code.
    # Otherwise use a generic 500 error code.
    if isinstance(exception, webapp2.HTTPException):
      self.response.set_status(exception.code)
    else:
      self.response.set_status(500)

    msg = {"error": exception.__class__.__name__, "message": str(exception)}
    self.response.out.write(json.dumps(msg))

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


def build_service(service_name, api_version, scopes):
  """Get an authorized service account http connection"""
  if DEBUG:
    if config.SERVICE_EMAIL and config.SERVICE_KEY_PATH and os.path.exists(config.SERVICE_KEY_PATH):
      from oauth2client.client import SignedJwtAssertionCredentials
      # must extract key first since pycrypto doesn't support p12 files
      # openssl pkcs12 -passin pass:notasecret -in privatekey.p12 -nocerts -passout pass:notasecret -out key.pem
      # openssl pkcs8 -nocrypt -in key.pem -passin pass:notasecret -topk8 -out privatekey.pem
      # rm key.pem
      key_str = open(config.SERVICE_KEY_PATH).read()
      credentials = SignedJwtAssertionCredentials(
        config.SERVICE_EMAIL,
        key_str,
        scopes)
      http = credentials.authorize(httplib2.Http(api.memcache))
      return build(service_name, api_version, http=http)
    else:
      logging.warn("Please create a service account and download your key add to appengine_config.py.")
      raise AppError("Service '{}' not availble from localhost without a service account set up and added to appengine_config.py.".format(service_name))
  credentials = AppAssertionCredentials(scope=scopes)
  http = credentials.authorize(httplib2.Http(api.memcache))
  return build(service_name, api_version, http=http)


# Leave minification etc up to PageSpeed
def compile_js(files, exports=None, raw_js=None):
  def compile():
    js = "(function(root) {\n" if exports else ""
    for fname in files:
      with open(fname) as f:
        js += f.read() + "\n"
    if exports:
      for export in exports:
        js += "tailbone.{} = {};\n".format(export, export)
      # for public, private in exports.iteritems():
      #   submodules = public.split(".")[:-1]
      #   for i in range(len(submodules)):
      #     submodule = ".".join(submodules[:i+1])
      #     js += "root.{} = root.{} || {{}};\n".format(submodule, submodule)
      #   js += "root.{} = {};\n".format(public, private)
      if raw_js:
        js += "\n{}\n".format(raw_js)
      js += "})(this);\n"
    return js
  if DEBUG:
    return compile
  return compile()


# Find all javascript files in included modules
def compile_tailbone_js():
  combined_js = "var tailbone = {};\n"
  with open("tailbone/globals.js") as f:
    combined_js += f.read() + "\n"
  with open("app.yaml") as f:
    appyaml = yaml.load(f)
    for include in appyaml.get("includes", []):
      try:
        if include.startswith("tailbone"):
          module = __import__(include.replace("/", "."), globals(), locals(), ["EXPORTED_JAVASCRIPT"], -1)
          javascript = getattr(module, "EXPORTED_JAVASCRIPT", None)
          if javascript:
            if callable(javascript):
              combined_js += javascript() + "\n"
            else:
              combined_js += javascript + "\n"
      except ImportError as e:
        pass
  combined_js += """
//exports to multiple environments
if (typeof define === 'function' && define.amd) {
//AMD
define(function(){ return tailbone; });
} else if (typeof module != "undefined" && module.exports) {
//Node
module.exports = tailbone;
}
"""
  return combined_js

tailbone_js = compile_tailbone_js()

class JsHandler(webapp2.RequestHandler):
  def get(self):
    self.response.headers["Content-Type"] = "text/javascript"
    if DEBUG:
      self.response.out.write(compile_tailbone_js())
    else:
      # set cache-control public
      self.response.headers["Cache-Control"] = "public, max-age=300"
      self.response.out.write(tailbone_js)


class LoginHandler(webapp2.RequestHandler):
  def get(self):
    if not config.login_hook(self):
      self.redirect(
          config.create_login_url(
            self.request.get("continue", default_value="/")))


class LogoutHandler(webapp2.RequestHandler):
  def get(self):
    if not config.logout_hook(self):
      self.redirect(
          config.create_logout_url(
            self.request.get("continue", default_value="/")))

class LoginHelperHandler(webapp2.RequestHandler):
  def get(self):
    # run the create_user_hook
    self.response.out.write("""<!doctype html>
<html>
  <head>
    <title></title>
    <style type="text/css">
      * { margin: 0; padding: 0; }
    </style>
  </head>
  <body>
    If this window should have been automatically closed, you may not have javascript enabled.
    <script type="text/javascript">
      var targetOrigin = ( window.location.protocol + "//" + window.location.host );
      window.opener.postMessage({"ok" : true}, targetOrigin);
      window.close();
    </script>
  </body>
</html>""")


EXPORTED_JAVASCRIPT = compile_js([
  "tailbone/authentication.js"
], ["login", "logout", "login_url", "logout_url", "authorized"])

auth = webapp2.WSGIApplication([
  (r"{}login".format(PREFIX), LoginHandler),
  (r"{}logout" .format(PREFIX), LogoutHandler),
  (r"{}logup".format(PREFIX), LoginHelperHandler),
], debug=DEBUG, config=config.CONFIG)

app = webapp2.WSGIApplication([
  (r"/tailbone.js", JsHandler),
], debug=DEBUG, config=config.CONFIG)

class AddSlashHandler(webapp2.RequestHandler):
  def get(self):
    url = self.request.path + "/"
    if self.request.query_string:
      url += "?" + self.request.query_string
    self.redirect(url)

add_slash = webapp2.WSGIApplication([
  (r".*", AddSlashHandler)
], debug=DEBUG, config=config.CONFIG)
