# shared resources and global variables
from tailbone import *

class AdminHandler(BaseHandler):
  """Admin routes"""
  @as_json
  def get(self, action):
    if not api.users.is_current_user_admin():
      raise LoginError("You must be an admin.")
    def notFound(self):
      self.error(404)
      return {"error": "Not Found"}
    return {
    }.get(action, notFound)(self)

app = webapp2.WSGIApplication([
  (r"{}admin/.*".format(PREFIX), AdminHandler),
  ], debug=DEBUG)
