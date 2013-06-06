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
from tailbone import DEBUG

import webapp2

NONMUTATING = ["clocksync"]


# Test Handler
# ------------
#
# QUnit tests can only be preformed on the local host because they actively modify the database and
# don't properly clean up after themselves yet.
class TestHandler(webapp2.RequestHandler):
  def get(self, path):
    if DEBUG or path in NONMUTATING:
      try:
        with open("tailbone/test/{}.html".format(path)) as f:
          self.response.out.write(f.read())
      except:
        self.response.out.write("No such test found.")
    else:
      self.response.out.write("Sorry, most tests can only be run from localhost because they modify the \
      datastore.")

app = webapp2.WSGIApplication([
  (r"/test/?(.*)", TestHandler),
], debug=DEBUG)
