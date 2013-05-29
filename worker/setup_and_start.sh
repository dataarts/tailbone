#!/bin/bash

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

wget https://pypi.python.org/packages/source/t/tornado/tornado-3.0.1.tar.gz
tar xvfz tornado-3.0.1.tar.gz
cd tornado-3.0.1
python setup.py build
python setup.py install
cd ..

python -c '
import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
 
class WSHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print "new connection"
        self.write_message("Hello World")
      
    def on_message(self, message):
        print "message received %s" % message
 
    def on_close(self):
      print "connection closed"
 
 
application = tornado.web.Application([
    (r"/ws", WSHandler),
])
 
if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
' &
