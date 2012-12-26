import urllib
import webapp2

from google.appengine.api import urlfetch

# Simple Proxy Server
# ---------------------
#
# Simple proxy server should you need it. Comment out the code in app.yaml to enable.
#
class ProxyHandler(webapp2.RequestHandler):
  def proxy(self, *args, **kwargs):
    url = urllib.unquote(self.request.get('url'))
    if url:
      resp = urlfetch.fetch(url, method=self.request.method, headers=self.request.headers)
      for k,v in resp.headers.iteritems():
        self.response.headers[k] = v
      self.response.status = resp.status_code
      self.response.out.write(resp.content)
    else:
      self.response.out.write("Must provide a 'url' parameter.")
  def get(self, *args, **kwargs):
    self.proxy(*args, **kwargs)
  def put(self, *args, **kwargs):
    self.proxy(*args, **kwargs)
  def post(self, *args, **kwargs):
    self.proxy(*args, **kwargs)
  def delete(self, *args, **kwargs):
    self.proxy(*args, **kwargs)


app = webapp2.WSGIApplication([
  (r".*", ProxyHandler),
  ], debug=DEBUG)

