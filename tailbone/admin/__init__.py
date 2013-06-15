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

def ban(self):
  return {}

def notFound(self):
  self.error(404)
  return {"error": "Not Found"}

class AdminShortcutHandler(BaseHandler):
  @as_json
  def get(self, action):
    return {
        "ban": ban
    }.get(action, notFound)(self)

app = webapp2.WSGIApplication([
  (r"{}admin/(.*)".format(PREFIX), AdminShortcutHandler),
  ], debug=DEBUG)
