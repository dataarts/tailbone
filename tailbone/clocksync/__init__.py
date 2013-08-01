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

from tailbone import DEBUG, PREFIX, compile_js, as_json, BaseHandler

import time
import webapp2


class ClockSyncHandler(BaseHandler):
  def head(self):
    self.response.headers['Last-Modified'] = "{:f}".format(time.time()*1000)

  @as_json
  def get(self):
    return time.time()*1000

EXPORTED_JAVASCRIPT = compile_js([
  "tailbone/clocksync/clocksync.js",
], ["clocksync"])

app = webapp2.WSGIApplication([
  (r"{}clocksync/?.*".format(PREFIX), ClockSyncHandler),
], debug=DEBUG)
