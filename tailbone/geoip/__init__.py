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

from tailbone import as_json
from tailbone import BaseHandler
from tailbone import DEBUG

import webapp2
import json

class GeoIPHandler(BaseHandler):
  @as_json
  def get(self):
    if DEBUG:
      return {
        "Country": "US",
        "Region": "ca",
        "CityLatLong": {
          "lat": 37.7749,
          "lon": -122.4194,
        },
        "IP": "127.0.0.1",
        "City": "san francisco",
       }
    resp = {}
    for x in ["Country", "Region", "City", "CityLatLong"]:
      k = "X-AppEngine-" + x
      value = self.request.headers.get(k)
      if x == "CityLatLong" and value:
        value = [float(v) for v in value.split(",")]
        value = {
          "lat": value[0],
          "lon": value[1],
        }
      resp[x] = value
    resp["IP"] = self.request.remote_addr
    return resp

app = webapp2.WSGIApplication([
  (r".*", GeoIPHandler),
  ], debug=DEBUG)
