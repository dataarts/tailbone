import webapp2

class CustomHandler(webapp2.RequestHandler):
  def get(self):
    self.response.out.write("""
<html>
<head></head>
<body>
custom content or actions
</body>
</html>""")

app = webapp2.WSGIApplication([('.*', CustomHandler)])
