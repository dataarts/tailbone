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

import urllib
import webapp2
from tailbone import DEBUG

from google.appengine.api import urlfetch
from google.appengine.api import lib_config


class _ConfigDefaults(object):
  # list of valid domain to restrict proxy to defaults to anything
  RESTRICTED_DOMAINS = None

_config = lib_config.register('tailboneProxy', _ConfigDefaults.__dict__)


# Simple Proxy Server
# ---------------------
#
# Simple proxy server should you need it. Comment out the code in app.yaml to enable.
#
class ProxyHandler(webapp2.RequestHandler):
  def proxy(self, *args, **kwargs):
    url = urllib.unquote(self.request.get('url'))
    # TODO: check agains RESTRICTED_DOMAINS 
    if url:
      if _config.RESTRICTED_DOMAINS:
        if url not in _config.RESTRICTED_DOMAINS:
          self.error(500)
          self.response.out.write("Restricted domain.")
          return
      resp = urlfetch.fetch(url, method=self.request.method, headers=self.request.headers)
      for k,v in resp.headers.iteritems():
        self.response.headers[k] = v
      self.response.status = resp.status_code
      self.response.out.write(resp.content)
    else:
      self.error(500)
      self.response.out.write("Must provide a 'url' parameter.")
  def get(self, *args, **kwargs):
    self.proxy(*args, **kwargs)
  def put(self, *args, **kwargs):
    self.proxy(*args, **kwargs)
  def post(self, *args, **kwargs):
    self.proxy(*args, **kwargs)
  def delete(self, *args, **kwargs):
    self.proxy(*args, **kwargs)


app = webapp2.WSGIApplication([
  (r".*", ProxyHandler),
  ], debug=DEBUG)

