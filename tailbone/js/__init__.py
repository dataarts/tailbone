# shared resources and global variables
from tailbone import *

import webapp2

# Test Handler
# ------------
#
# QUnit tests can only be preformed on the local host because they actively modify the database and
# don't properly clean up after themselves yet.
class TestHandler(webapp2.RequestHandler):
  def get(self):
    if DEBUG:
      with open('tailbone/js/test_restful.html') as f:
        self.response.out.write(f.read())
    else:
      self.response.out.write("Sorry, tests can only be run from localhost because they modify the \
      datastore.")

app = webapp2.WSGIApplication([
  (r".*", TestHandler),
  ], debug=DEBUG)

