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

re_json = re.compile(r"^application/json", re.IGNORECASE)

# Parse the body of an upload based on the type if you are trying to post a cgi.FieldStorage object
# you should instead upload those blob separately via the special /api/files url.
def parse_body(self):
  if re_json.match(self.request.content_type):
    data = json.loads(self.request.body)
  else:
    data = {}
    for k,v in self.request.POST.items():
      if isinstance(v, cgi.FieldStorage):
        raise AppError("Files should be uploaded separately as their own form to /api/files/ and \
            then their ids should be uploaded and stored with the object.")
      if type(v) in [str, unicode]:
        v = json.loads(v)
      if data.has_key(k):
        current = data[k]
        if isinstance(current, list):
          current.append(v)
        else:
          data[k] = [current,v]
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


