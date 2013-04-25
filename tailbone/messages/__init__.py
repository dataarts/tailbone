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

from tailbone import *

import json
import random
import string
import webapp2

from google.appengine.api import channel


class MessagesHandler(BaseHandler):
  @as_json
  def get(self):
    # randomly generate client_id
    # collision probability with 5000 concurrent users and 8 letter client_id = 0.00005985635
    # 1 - e^(-(5000^2)/(2*26^8))
    client_id = ''.join(random.choice(string.lowercase) for x in range(8))
    return {
      "token": channel.create_channel(client_id),
      "client_id": client_id
    }

  @as_json
  def post(self):
    body = self.request.body
    data = json.loads(body)
    to = data.get("to")
    if not to:
      raise AppError("Must provide a 'to' client_id.")
    channel.send_message(to, body)

app = webapp2.WSGIApplication([
  (r"{}messages/?".format(PREFIX), MessagesHandler),
], debug=DEBUG)
