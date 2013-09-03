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
from tailbone import AppError
from tailbone import config
from tailbone import DEBUG
from tailbone import PREFIX
from tailbone.compute_engine import LoadBalancer
from tailbone.compute_engine import TailboneCEInstance
from tailbone.compute_engine import STARTUP_SCRIPT_BASE

import binascii
from hashlib import sha1
import hmac
import md5
import time
import webapp2

from google.appengine.api import lib_config


class _ConfigDefaults(object):
  PARAMS = {}
  SOURCE_SNAPSHOT = None
  STARTUP_SCRIPT = """
echo "You should edit the appengine_config.py file with your own startup_script."
"""
  def calc_load(stats):
    return TailboneCEInstance.calc_load(stats)


_config = lib_config.register('tailboneCustomCE', _ConfigDefaults.__dict__)

# Prefixing internal models with Tailbone to avoid clobbering when using RESTful API
class TailboneCustomInstance(TailboneCEInstance):
  SOURCE_SNAPSHOT = _config.SOURCE_SNAPSHOT
  PARAMS = dict(dict(TailboneCEInstance.PARAMS, **{
    "name": "custom-id",
    "metadata": {
      "items": [
        {
          "key": "startup-script",
          "value": STARTUP_SCRIPT_BASE + _config.STARTUP_SCRIPT,
        },
      ],
    }
  }), **_config.PARAMS)

  @staticmethod
  def calc_load(stats):
    return _config.calc_load(stats)


class CustomHandler(BaseHandler):
  @as_json
  def get(self):
    instance = LoadBalancer.find(TailboneCustomInstance)
    if not instance:
      raise AppError('Instance not found, try again later.')
    return {
      "ip": instance.address
    }

app = webapp2.WSGIApplication([
  (r"{}customce/?.*".format(PREFIX), CustomHandler),
], debug=DEBUG)