# shared resources and global variables
from tailbone import *

class AbuseHandler(BaseHandler):
  def get(self):
    self.response.out.write("""
<!doctype html>
<html>
  <head>
    <script src="//ajax.googleapis.com/ajax/libs/jquery/1.9.0/jquery.min.js"></script>
  </head>
  <body>
    Block/Unblock User:
    <form>
    <input type="text" />
    <input type="submit" />
    </form>
    <script>
    </script>
  </body>
</html>
""")

def ban(self):
  return {}

def notFound(self):
  self.error(404)
  return {"error": "Not Found"}

class AdminShortcutHandler(BaseHandler):
  @as_json
  def get(self, action):
    return {
        "ban": ban
    }.get(action, notFound)(self)

app = webapp2.WSGIApplication([
  (r"{}admin/abuse".format(PREFIX), AbuseHandler),
  (r"{}admin/(.*)".format(PREFIX), AdminShortcutHandler),
  ], debug=DEBUG)
