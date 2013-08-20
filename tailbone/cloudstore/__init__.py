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

import os
import webapp2 

from tailbone import DEBUG
from tailbone import PREFIX

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import lib_config 
from google.appengine.api import app_identity

class _ConfigDefaults(object):
  BUCKET = app_identity.get_application_id()

_config = lib_config.register('tailboneCloudstore', _ConfigDefaults.__dict__)


class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
  def get(self, resource):
    filename = "/gs/{}/{}".format(_config.BUCKET, resource)
    key = blobstore.create_gs_key(filename)
    self.send_blob(key)

app = webapp2.WSGIApplication([
  (r"{}cloudstore/(.*)".format(PREFIX), ServeHandler)
], debug=DEBUG)
