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

# Rewrites any path to the index.html file for html5mode history and location.

# shared resources and global variables
from tailbone import DEBUG
from tailbone.static.protected import _config

import webapp2
import yaml

# index.html is symlinked to api/client/index.html
index = None
with open("tailbone/pathrewrite/index.html") as f:
  index = f.read()

is_protected = False
with open("app.yaml") as f:
  appyaml = yaml.load(f)
  includes = [i for i in appyaml.get("includes", [])]
  is_protected = "tailbone/static/protected" in includes
  if is_protected:
    path = "client/" + _config.BASE_PATH + "/index.html"
    with open(path) as f:
        index = f.read()


# Pathrewrite Handler
# ------------
#
# Proxies any page to the base url
class PathrewriteHandler(webapp2.RequestHandler):
  def get(self):
    if is_protected:
      authorized = _config.is_authorized(self.request)
      if not authorized:
        self.response.out.write(
          _config.unauthorized_response(self.request))
        return
    self.response.out.write(index)

app = webapp2.WSGIApplication([
  (r"^[^.]*$", PathrewriteHandler),
], debug=DEBUG)
