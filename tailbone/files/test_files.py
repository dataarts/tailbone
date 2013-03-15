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

import datetime
import json
import os
import random
import tailbone.files as app
import time
import unittest
import webapp2
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.ext import testbed
from google.appengine.api.blobstore import file_blob_storage
from google.appengine.api.blobstore import blobstore_stub
from google.appengine.api.files import file_service_stub
import itertools
import mimetools
import mimetypes
from StringIO import StringIO
import urllib
import urllib2

class MultiPartForm(object):
  """Accumulate the data to be used when posting a form."""

  def __init__(self):
    self.form_fields = []
    self.files = []
    self.boundary = mimetools.choose_boundary()
    return

  def get_content_type(self):
    return 'multipart/form-data; boundary=%s' % self.boundary

  def add_field(self, name, value):
    """Add a simple field to the form data."""
    self.form_fields.append((name, value))
    return

  def add_file(self, fieldname, filename, fileHandle, mimetype=None):
    """Add a file to be uploaded."""
    body = fileHandle.read()
    if mimetype is None:
      mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    self.files.append((fieldname, filename, mimetype, body))
    return

  def __str__(self):
    """Return a string representing the form data, including attached files."""
    # Build a list of lists, each containing "lines" of the
    # request.  Each part is separated by a boundary string.
    # Once the list is built, return a string where each
    # line is separated by '\r\n'.
    parts = []
    part_boundary = '--' + self.boundary

    # Add the form fields
    parts.extend(
      [ part_boundary,
        'Content-Disposition: form-data; name="%s"' % name,
        '',
        value,
      ]
      for name, value in self.form_fields
      )

    # Add the files to upload
    parts.extend(
      [ part_boundary,
        'Content-Disposition: file; name="%s"; filename="%s"' % \
         (field_name, filename),
        'Content-Type: %s' % content_type,
        '',
        body,
      ]
      for field_name, filename, content_type, body in self.files
      )

    # Flatten the list and add closing boundary marker,
    # then return CR+LF separated data
    flattened = list(itertools.chain(*parts))
    flattened.append('--' + self.boundary + '--')
    flattened.append('')
    return '\r\n'.join(flattened)

class TestbedWithFiles(testbed.Testbed):

  def init_blobstore_stub(self):
    blob_storage = file_blob_storage.FileBlobStorage('/tmp/testbed.blobstore',
                        testbed.DEFAULT_APP_ID)
    blob_stub = blobstore_stub.BlobstoreServiceStub(blob_storage)
    file_stub = file_service_stub.FileServiceStub(blob_storage)
    self._register_stub('blobstore', blob_stub)
    self._register_stub('file', file_stub)

class TestCase(unittest.TestCase):

  def setUp(self):
    self.testbed = TestbedWithFiles()
    self.testbed.activate()
    self.testbed.init_datastore_v3_stub()
    self.testbed.init_blobstore_stub()
    self.testbed.init_memcache_stub()
    self.testbed.init_taskqueue_stub()
    self.testbed.init_user_stub()
    self.model_url = "/api/todos/"
    self.user_url = "/api/users/"
    self.user_id = "118124022271294486125"
    self.setCurrentUser("test@gmail.com", self.user_id, True)

  def tearDown(self):
    self.testbed.deactivate()

  def setCurrentUser(self, email, user_id, is_admin=False):
    self.testbed.setup_env(
        APP_ID = "testbed",
        USER_EMAIL = email or '',
        USER_ID = user_id or '',
        USER_IS_ADMIN = '1' if is_admin else '0',
        overwrite = True,
        )

  def assertJsonResponseData(self, response, data):
    self.assertEqual(response.headers["Content-Type"], "application/json")
    response_data = json.loads(response.body)
    ignored_list = []
    if not data.has_key("Id"):
      ignored_list.append("Id")
    if not data.has_key("owners"):
      ignored_list.append("owners")
    if not data.has_key("viewers"):
      ignored_list.append("viewers")
    for ignored in ignored_list:
      if response_data.has_key(ignored):
        del response_data[ignored]
      if data.has_key(ignored):
        del data[ignored]
    self.assertEqual(data, response_data)

  def test_file_upload(self):
    request = webapp2.Request.blank("/api/files/create")
    request.method = "GET"
    response = request.get_response(app.app)
    self.assertJsonResponseData(response, {
        "upload_url": "http://testbed.example.com/_ah/upload/agx0ZXN0YmVkLXRlc3RyGwsSFV9fQmxvYlVwbG9hZFNlc3Npb25fXxgBDA"
      })
    upload_url = json.loads(response.body).get("upload_url")
    upload_url = upload_url[26:]

    # TODO: does not seem to work yet in stub though live test works at /api/upload_test.html
#
#     form = MultiPartForm()
#
#     # Add a fake file
#     form.add_file("file", "file.txt",
#                   fileHandle=StringIO("Some big file object."))
#
#     # Build the request
#     request = webapp2.Request.blank(upload_url)
#     body = str(form)
#     request.method = "POST"
#     request.headers["Content-Length"] = len(body)
#     request.headers["Content-Type"] = "multipart/form-data"
#     # request.headers["Content-Type"] = form.get_content_type()
#     request.body = body
#     response = request.get_response(app.app)
#     print("response %s" % response)
#     self.assertJsonResponseData(response, [
#       {
#         "filename": "file"
#       }])
