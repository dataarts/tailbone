# Rewrites any path to the index.html file for html5mode history and location.

# shared resources and global variables
from tailbone import *

import webapp2

# index.html is symlinked to api/client/index.html
index = None
with open('tailbone/pathrewrite/index.html') as f:
  index = f.read()

# Pathrewrite Handler
# ------------
#
# Proxies any page to the base url
class PathrewriteHandler(webapp2.RequestHandler):
  def get(self):
    self.response.out.write(index)

app = webapp2.WSGIApplication([
  (r"^[^.]*$", PathrewriteHandler),
  ], debug=DEBUG)
