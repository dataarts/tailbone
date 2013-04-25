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

from tailbone import DEBUG, PREFIX
import webapp2

from google.appengine import api


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


class Middleware(object):
  def __init__(self, app):
    self.app = app

  def __call__(self, environ, start_response):
    environ["USER_ID"] = api.users.get_current_user().user_id()
    req = webapp2.Request(environ)
    resp = req.get_response(self.app)
    return resp(environ, start_response)


app = webapp2.WSGIApplication([
  (r"{}login".format(PREFIX), LoginHandler),
  (r"{}logout" .format(PREFIX), LogoutHandler),
], debug=DEBUG)
