import datetime
import json
import os
import random
import tailbone.restful as app
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

class TestCase(unittest.TestCase):

  def setUp(self):
    self.testbed = testbed.Testbed()
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

  def create(self, url, data):
    request = webapp2.Request.blank(url)
    request.method = "POST"
    request.headers["Content-Type"] = "application/json"
    request.body = json.dumps(data)
    response = request.get_response(app.app)
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


  def test_query_by_id(self):
    data = {"text": "example"}
    response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank(self.model_url+str(response_data["Id"]))
    response = request.get_response(app.app)

    self.assertJsonResponseData(response, data)

  def test_query_all(self):
    num_items = 3
    data = {"text": "example"}
    for i in xrange(num_items):
      response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank(self.model_url)
    response = request.get_response(app.app)
    items = json.loads(response.body)
    self.assertEqual(len(items), num_items)
    self.assertEqual(response.headers["Content-Type"], "application/json")

  def test_query_gte_json_params(self):
    num_items = 3
    for i in xrange(num_items):
      data = {"text": i+0.1}
      response, response_data = self.create(self.model_url, data)
    data = {"text": 2}
    response, response_data = self.create(self.model_url, data)

    params = {
        "filter": ["text",">=",1]
        }
    request = webapp2.Request.blank("{}?params={}".format(self.model_url, json.dumps(params)))
    response = request.get_response(app.app)
    items = json.loads(response.body)
    self.assertEqual(len(items), 3)

  def test_query_gte(self):
    num_items = 3
    for i in xrange(num_items):
      data = {"text": i+0.1}
      response, response_data = self.create(self.model_url, data)
    data = {"text": 2}
    response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank("{}?filter=text>=1".format(self.model_url))
    response = request.get_response(app.app)
    items = json.loads(response.body)
    self.assertEqual(len(items), 3)

  def test_query_bool(self):
    num_items = 3
    for i in xrange(num_items):
      data = {"text": True}
      response, response_data = self.create(self.model_url, data)
    data = {"text": False}
    response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank("{}?filter=text==true".format(self.model_url))
    response = request.get_response(app.app)
    items = json.loads(response.body)
    self.assertEqual(len(items), num_items)

  def test_query_in(self):
    pass

  def test_query_subobject(self):
    num_items = 3
    for i in xrange(num_items):
      data = {"text": {"sub": True}}
      response, response_data = self.create(self.model_url, data)
    data = {"text": {"sub": False}}
    response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank("{}?filter=text.sub==true".format(self.model_url))
    response = request.get_response(app.app)
    items = json.loads(response.body)
    self.assertEqual(len(items), num_items)

  def test_query_OR_AND(self):
    num_items = 3
    for i in xrange(num_items):
      data = {"text": i}
      response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank("{}?filter=OR(text==0, text==2)&order=text&order=key".format(self.model_url))
    response = request.get_response(app.app)
    items = json.loads(response.body)
    self.assertEqual(len(items), 2)

  def test_query_projection(self):
    num_items = 3
    for i in xrange(num_items):
      data = {"Value": i, "other": i}
      response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank("{}?filter=Value>0&projection=Value".format(self.model_url))
    response = request.get_response(app.app)
    items = json.loads(response.body)
    self.assertEqual(items[0], {"Value":1, "Id": 2})
    self.assertEqual(len(items), 2)

  def test_order_asc(self):
    num_items = 3
    for i in xrange(num_items):
      data = {"text": i}
      response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank("{}?order=text".format(self.model_url))
    response = request.get_response(app.app)
    items = json.loads(response.body)
    self.assertEqual(items[0], {"text":0, "Id": 1, "owners": ["limOwBmjSigmf"], "viewers": []})
    self.assertEqual(len(items), num_items)

  def test_order_desc(self):
    num_items = 3
    for i in xrange(num_items):
      data = {"text": i}
      response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank("{}?order=-text".format(self.model_url))
    response = request.get_response(app.app)
    items = json.loads(response.body)
    self.assertEqual(items[0], {"text":2, "Id": 3, "owners": ["limOwBmjSigmf"], "viewers": []})
    self.assertEqual(len(items), num_items)

  def test_user_create_and_update(self):
    self.setCurrentUser("test@gmail.com", self.user_id, True)
    data = {"text": "example"}
    response, response_data = self.create(self.user_url, data)
    data["Id"] = "limOwBmjSigmf"
    self.assertEqual(json.dumps(data), json.dumps(response_data))

    request = webapp2.Request.blank(self.user_url+str(response_data["Id"]))
    data = {"text": "new text"}
    request.method = "PUT"
    request.headers["Content-Type"] = "application/json"
    request.body = json.dumps(data)
    response = request.get_response(app.app)
    data["Id"] = "limOwBmjSigmf"
    self.assertJsonResponseData(response, data)

  def test_user_get_me(self):
    self.setCurrentUser("test@gmail.com", self.user_id, True)
    request = webapp2.Request.blank(self.user_url+"me")
    request.method = "GET"
    request.headers["Content-Type"] = "application/json"
    response = request.get_response(app.app)
    from tailbone import convert_num_to_str
    data = {
        "Id": convert_num_to_str(self.user_id),
        "email": "test@gmail.com",
        "$unsaved": True,
        }
    self.assertJsonResponseData(response, data)

  def test_get_user_by_id(self):
    self.setCurrentUser("test@gmail.com", self.user_id, True)
    data = {"text": "example"}
    response, response_data = self.create(self.user_url, data)
    request = webapp2.Request.blank(self.user_url+str(response_data["Id"]))
    request.method = "GET"
    request.headers["Content-Type"] = "application/json"
    response = request.get_response(app.app)
    from tailbone import convert_num_to_str
    data["Id"] = convert_num_to_str(self.user_id)
    self.assertJsonResponseData(response, data)
    request = webapp2.Request.blank(self.user_url+"me")
    request.method = "GET"
    request.headers["Content-Type"] = "application/json"
    request.body = json.dumps(data)
    response = request.get_response(app.app)
    self.assertJsonResponseData(response, data)

  def test_user_illegal(self):
    self.setCurrentUser("test@gmail.com", "8", True)
    data = {"text": "example"}
    response, response_data = self.create(self.user_url, data)
    self.setCurrentUser("test@gmail.com", "7", True)
    request = webapp2.Request.blank(self.user_url+str(response_data["Id"]))
    data = {"text": "new text"}
    request.method = "PUT"
    request.headers["Content-Type"] = "application/json"
    request.body = json.dumps(data)
    response = request.get_response(app.app)
    self.assertJsonResponseData(response,
        { "error": "AppError",
          "message": "Id must be the current user_id or me. " +
          "User h tried to modify user i."})

  def test_user_query_all(self):
    num_items = 3
    data = {"text": "example"}
    for i in xrange(num_items):
      self.setCurrentUser("test@gmail.com", str(i), True)
      response, response_data = self.create(self.user_url, data)

    self.setCurrentUser(None, None)
    request = webapp2.Request.blank(self.user_url)
    response = request.get_response(app.app)
    items = json.loads(response.body)
    self.assertEqual(len(items), num_items)
    self.assertEqual(response.headers["Content-Type"], "application/json")


  def test_ownership(self):
    # create model
    data = {
        "private_stuff": "thing",
        "PublicStuff": "otherthing"
        }
    self.setCurrentUser("test@gmail.com", self.user_id, True)
    response, response_data = self.create(self.model_url, data)
    data["Id"] = 1
    self.assertJsonResponseData(response, data)
    # edit model
    data["private_stuff"] = "newthing"
    response, response_data = self.create(self.model_url, data)
    self.assertJsonResponseData(response, data)
    # get public params
    self.setCurrentUser("test2@gmail.com", "2342343242", False)
    request = webapp2.Request.blank(self.model_url + "1")
    request.method = "GET"
    request.headers["Content-Type"] = "application/json"
    response = request.get_response(app.app)
    del data["private_stuff"]
    self.assertJsonResponseData(response, data)
    # edit from other account
    response, response_data = self.create(self.model_url, data)
    self.assertJsonResponseData(response, {
      "error": "AppError",
      "message": "You do not have sufficient privileges."
      })

  def test_create_with_url_encode(self):
    data = {"text": "new text"}
    request = webapp2.Request.blank(self.model_url)
    request.method = "POST"
    request.headers["Content-Type"] = "application/x-www-form-urlencoded"
    request.body = urllib.urlencode(data)
    response = request.get_response(app.app)
    response_data = json.loads(response.body)
    data["Id"] = 1
    self.assertJsonResponseData(response, data)


  def test_create_without_login(self):
    data = {"test": "info"}
    self.setCurrentUser(None, None)
    response, response_data = self.create(self.model_url, data)
    self.assertJsonResponseData(response, {
      "error": "LoginError",
      "message": "User must be logged in.",
      "url": "https://www.google.com/accounts/Login?continue=http%3A//localhost/api/todos/"})

  def test_create_with_post(self):
    data = {"text": "example"}
    response, response_data = self.create(self.model_url, data)
    data["Id"] = 1
    self.assertJsonResponseData(response, data)

  def test_create_with_post_and_id(self):
    data = {"private": "test", "Public": "example", "Id": 4}
    response, response_data = self.create(self.model_url, data)
    self.assertJsonResponseData(response, data)

  def test_update_with_put(self):
    data = {"private": "test", "Public": "example"}
    response, response_data = self.create(self.model_url, data)
    data["Id"] = 1

    request = webapp2.Request.blank(self.model_url+str(response_data["Id"]))
    data["private"] = "new text"
    request.method = "PUT"
    request.headers["Content-Type"] = "application/json"
    request.body = json.dumps(data)
    response = request.get_response(app.app)
    self.assertJsonResponseData(response, data)

  def test_delete(self):
    data = {"text": "example"}
    response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank(self.model_url+str(response_data["Id"]))
    data = {"text": "example"}
    request.method = "DELETE"
    request.headers["Content-Type"] = "application/json"
    request.body = json.dumps(data)
    response = request.get_response(app.app)
    response_data = json.loads(response.body)
    self.assertEqual(json.dumps(response_data), json.dumps({}))

    request = webapp2.Request.blank(self.model_url)
    response = request.get_response(app.app)
    items = json.loads(response.body)
    self.assertEqual(len(items), 0)

  def test_put_to_create(self):
    pass

  def test_create_with_specific_id(self):
    pass

  def test_variable_data_same_class(self):
    data = {"text": "example"}
    response, response_data = self.create(self.model_url, data)
    data = {"different": "text"}
    response, response_data = self.create(self.model_url, data)
    data = {"different": "text", "subobject": {"more": 323232}}
    response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank(self.model_url)
    response = request.get_response(app.app)
    items = json.loads(response.body)

  def test_datetime(self):
    obj = datetime.datetime.now()
    ms = time.mktime(obj.utctimetuple()) * 1000
    ms += getattr(obj, "microseconds", 0) / 1000
    data = {"date": int(ms)}
    response, response_data = self.create(self.model_url, data)

    self.assertJsonResponseData(response, data)

  def test_large_text(self):
    data = {"text": "example" * 1000}
    response, response_data = self.create(self.model_url, data)

    self.assertJsonResponseData(response, data)

  def test_dict_property(self):
    data = {"obj": {"another": "obj"}}
    response, response_data = self.create(self.model_url, data)

    self.assertJsonResponseData(response, data)
