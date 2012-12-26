# shared resources and global variables
from tailbone import *

import re
import urllib

from google.appengine.api.images import delete_serving_url
from google.appengine.api.images import get_serving_url_async
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

re_image = re.compile(r"image/(png|jpeg|jpg|webp|gif|bmp|tiff|ico)", re.IGNORECASE)

def blob_info_to_dict(blob_info):
  d = {}
  for prop in ["content_type", "creation", "filename", "size"]:
    d[prop] = getattr(blob_info, prop)
  key = blob_info.key()
  if re_image.match(blob_info.content_type):
    d["image_url"] = get_serving_url_async(key)
  d["Id"] = str(key)
  return d

class FilesHandler(blobstore_handlers.BlobstoreDownloadHandler):
  @as_json
  def get(self, key):
    if key == "":
      current_user(required=True)
      return {
          "upload_url": blobstore.create_upload_url("/api/files/upload")
          }
    key = str(urllib.unquote(key))
    blob_info = blobstore.BlobInfo.get(key)
    if blob_info:
      self.send_blob(blob_info)
      raise BreakError
    else:
      self.error(404)
      return {"error": "File not found with key " + key}

  @as_json
  def post(self, _):
    raise AppError("You must make a GET call to /api/files to get a POST url.")

  @as_json
  def put(self, _):
    raise AppError("PUT is not supported for the files api.")

  @as_json
  def delete(self, key):
    current_user(required=True)
    key = blobstore.BlobKey(str(urllib.unquote(key)))
    blob_info = blobstore.BlobInfo.get(key)
    if blob_info:
      blob_info.delete()
      if re_image.match(blob_info.content_type):
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


