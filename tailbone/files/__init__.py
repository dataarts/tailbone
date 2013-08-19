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
from tailbone import AppError
from tailbone import PREFIX
from tailbone import as_json
from tailbone import BreakError
from tailbone import config
from tailbone import DEBUG
from tailbone import restful

import re
import urllib
import webapp2

HAS_PIL = True
try:
  import PIL
  from google.appengine.api.images import delete_serving_url
  from google.appengine.api.images import get_serving_url_async
except:
  HAS_PIL = False

from google.appengine.ext.ndb import blobstore
from google.appengine.ext import blobstore as bs
from google.appengine.ext.webapp import blobstore_handlers


re_image = re.compile(r"image/(png|jpeg|jpg|webp|gif|bmp|tiff|ico)", re.IGNORECASE)


class BlobInfo(blobstore.BlobInfo):
  def to_dict(self, *args, **kwargs):
    result = super(BlobInfo, self).to_dict(*args, **kwargs)
    result["Id"] = str(self.key())
    return result


def blob_info_to_dict(blob_info):
  d = {}
  for prop in ["content_type", "creation", "filename", "size"]:
    d[prop] = getattr(blob_info, prop)
  key = blob_info.key()
  if HAS_PIL and re_image.match(blob_info.content_type):
    d["image_url"] = get_serving_url_async(key)
  d["Id"] = str(key)
  return d


class FilesHandler(blobstore_handlers.BlobstoreDownloadHandler):

  @as_json
  def get(self, key):
    if key == "":  # query
      if not config.is_current_user_admin():
        raise AppError("User must be administrator.")
      return restful.query(self, BlobInfo)
    elif key == "create":
      return {
          "upload_url": blobstore.create_upload_url("/api/files/upload")
      }
    key = str(urllib.unquote(key))
    blob_info = bs.BlobInfo.get(key)
    if blob_info:
      self.send_blob(blob_info)
      raise BreakError
    else:
      self.error(404)
      return {"error": "File not found with key " + key}

  @as_json
  def post(self, _):
    raise AppError("You must make a GET call to /api/files/create to get a POST url.")

  @as_json
  def put(self, _):
    raise AppError("PUT is not supported for the files api.")

  @as_json
  def delete(self, key):
    if not config.is_current_user_admin():
      raise AppError("User must be administrator.")
    key = blobstore.BlobKey(str(urllib.unquote(key)))
    blob_info = BlobInfo.get(key)
    if blob_info:
      blob_info.delete()
      if HAS_PIL and re_image.match(blob_info.content_type):
        delete_serving_url(key)
      return {}
    else:
      self.error(404)
      return {"error": "File not found with key " + key}


class FilesUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
  @as_json
  def post(self):
    return [blob_info_to_dict(b) for b in self.get_uploads()]


app = webapp2.WSGIApplication([
  (r"{}files/upload".format(PREFIX), FilesUploadHandler),
  (r"{}files/?(.*)".format(PREFIX), FilesHandler),
], debug=DEBUG)
