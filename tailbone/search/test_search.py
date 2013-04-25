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
from tailbone import search
from tailbone import restful
import time
import unittest
import webapp2
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.ext import testbed
from google.appengine.api.blobstore import file_blob_storage
from google.appengine.api.blobstore import blobstore_stub
from google.appengine.api.files import file_service_stub
from google.appengine.api.search import simple_search_stub 
import itertools
import logging
import mimetools
import mimetypes
from StringIO import StringIO
import urllib
import urllib2


class TestCase(unittest.TestCase):

  def setUp(self):
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.testbed.init_datastore_v3_stub()
    self.testbed.init_blobstore_stub()
    self.testbed.init_memcache_stub()
    self.testbed.init_taskqueue_stub()
    self.testbed.init_user_stub()
    # TODO: Search stub does not exist
    # self.testbed.init_search_stub()
    search_stub = simple_search_stub.SearchServiceStub()
    self.testbed._register_stub("search", search_stub)
    self.model_url = "/api/todos/"
    self.user_url = "/api/users/"
    self.user_id = "118124022271294486125"
    self.setCurrentUser("test@gmail.com", self.user_id, True)
    search._searchable = None

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

  def create(self, url, data):
    request = webapp2.Request.blank(url)
    request.method = "POST"
    request.headers["Content-Type"] = "application/json"
    request.body = json.dumps(data)
    response = request.get_response(restful.app)
    self.assertEqual(response.headers["Content-Type"], "application/json")
    response_data = json.loads(response.body)
    return response, response_data

  def search(self, params, index_name=""):
    request = webapp2.Request.blank("/api/search/"+index_name+"?"+urllib.urlencode(params))
    request.method = "GET"
    request.headers["Content-Type"] = "application/json"
    response = request.get_response(restful.app)
    self.assertEqual(response.headers["Content-Type"], "application/json")
    response_data = json.loads(response.body)
    return response, response_data

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

  def test_search(self):
    test_search = r"""{
    "todos": {
      "Item": "TextField",
      "Place": "GeoField"
    }}"""
    search._searchable = search.compile_searchable(json.loads(test_search))
    data = {"Item": "example"}
    response, response_data = self.create(self.model_url, data)
    self.assertJsonResponseData(response, data)
    response, response_data = self.search({"q":"example"})
    # TODO: Search service stub not yet ready
    # data["Kind"] = "todos"
    # data["Id"] = 1
    # self.assertEqual(len(response_data), 1)
    # self.assertEqual(response_data, [data])
    # search._searchable = None
