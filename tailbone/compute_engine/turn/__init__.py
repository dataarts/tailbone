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

from tailbone import BaseHandler
from tailbone import as_json
from tailbone import config
from tailbone.compute_engine import TailboneCEInstance

import binascii
from hashlib import sha1
import hmac
import md5
import time

import webapp2

SECRET = "notasecret"

turn_script = open("tailbone/compute_engine/turn/setup_and_run.sh").read()

# Prefixing internal models with Tailbone to avoid clobbering when using RESTful API
class TailboneTurnInstance(TailboneCEInstance):
  PARAMS = dict(TailboneCEInstance.PARAMS, **{
    "name": "turn-id",
    "metadata": {
      "items": [
        {
          "key": "startup-script",
          "value": turn_script,
        },
      ],
    }
  })


def credentials(username):
  timestamp = str(time.mktime(time.gmtime())).split('.')[0]
  username = "{}:{}".format(username, timestamp)
  password = hmac.new(SECRET, username, sha1)
  password = binascii.b2a_base64(password.digest())[:-1]
  return username, password


class TurnHandler(BaseHandler):
  @as_json
  def get(self):
    username = self.request.get("username")
    if not username:
      raise AppError("Must provide username.")
    username, password = credentials(username)
    return {
      "username": username,
      "password": password,
      "turn": "some address"
    }

app = webapp2.WSGIApplication([
  (r"{}turn/?.*".format(config.PREFIX), TurnHandler),
], debug=config.DEBUG)