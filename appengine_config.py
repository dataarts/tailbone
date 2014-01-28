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


## Edit the code below to add you own hooks and modify tailbone's behavior

## Base Tailbone overrides and hooks

## Set the global default namespace
# def namespace_manager_default_namespace_for_request():
#   return "my_custom_namespace"

## Use JSONP for all apis
# tailbone_JSONP = False

## Use CORS for all apis
# tailbone_CORS = True
# tailbone_CORS_RESTRICTED_DOMAINS = ["http://localhost"]

## modify the below functions to change how users are identified
# tailbone_is_current_user_admin =
# tailbone_get_current_user =
# tailbone_create_login_url =
# tailbone_create_logout_url =
## Example of allowing anybody to write to the datastore by always using a fake user
# class FakeUser(object):
#   def user_id(self):
#     return "fakeuser"
# u = FakeUser()
# def fake_user():
#   return u
# tailbone_get_current_user = fake_user

## Use google plus for login and identity
#CLIENT_ID = ''
#CLIENT_SECRET = ''

#def gplusFriends(gplus, http, token=None):
  #result = gplus.people().list(userId='me', collection='visible', pageToken=token, orderBy='best').execute(http=http)
  #token = result.pop('nextPageToken', None)
  #if token:
    #result['items'] += gplusFriends(gplus, http, token).get('items', [])
  #return result


#class GPlusUser(object):
  #def __init__(self, user_id=None, credentials=None):
    #self.__user_id = user_id
    #self.__credentials = credentials
  #def user_id(self):
    #return self.__user_id
  #def friends(self):
    #import httplib2
    #http = httplib2.Http()
    #http = self.__credentials.authorize(http)
    #from apiclient.discovery import build
    #gplus = build('plus', 'v1')
    #return gplusFriends(gplus, http)
  #def profile(self):
    #import httplib2
    #http = httplib2.Http()
    #http = self.__credentials.authorize(http)
    #from apiclient.discovery import build
    #gplus = build('plus', 'v1')
    ## fetch me
    #result = gplus.people().get(userId='me').execute(http=http)
    #return result

#import webapp2
#from webapp2_extras import sessions
#def get_current_user(*args, **kwargs):
  ## get webapp2
  ## get session
  ## get user from session
  #request = webapp2.get_request()
  #session_store = sessions.get_store(request=request)
  #session = session_store.get_session()
  #credentials = session.get('credentials', None)
  #if credentials:
    #from oauth2client.client import OAuth2Credentials
    #credentials = OAuth2Credentials.from_json(credentials)
    #user_id = session.get('gplus_id', None)
    #user = GPlusUser(user_id, credentials)
    #return user
  #return None

#tailbone_get_current_user = get_current_user

#scope = 'https://www.googleapis.com/auth/plus.login'
#redirect_path = '/api/login'

#def secret():
  #import random
  #import string
  #return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))

#def create_login_url(dest_url=None, **kwargs):
  #request = webapp2.get_request()
  #session_store = sessions.get_store(request=request)
  #session = session_store.get_session()
  #state = {
      #'secret': session.get('secret')
  #}
  #if dest_url:
    #state['continue'] =  dest_url
  #import json
  #state = json.dumps(state)
  #redirect_uri = request.host_url + redirect_path
  #url = 'https://accounts.google.com/o/oauth2/auth?\
#scope={}&\
#state={}&\
#redirect_uri={}&\
#response_type=code&\
#client_id={}&\
#access_type=offline'.format(scope, state, redirect_uri, CLIENT_ID)
  #return url

#tailbone_create_login_url = create_login_url

#def create_logout_url(dest_url):
  #return dest_url

#tailbone_create_logout_url = create_logout_url

#def destroy_user(self):
  ##clear the local session and call the revoke_uri
  #request = webapp2.get_request()
  #session_store = sessions.get_store(request=request)
  #session = session_store.get_session()
  #credentials = session.pop('credentials', None)
  #gplus_id = session.pop('gplus_id', None)
  #if credentials:
    #from oauth2client.client import OAuth2Credentials
    #credentials = OAuth2Credentials.from_json(credentials)
    #revoke_uri = str("%s?token=%s" % (credentials.revoke_uri, credentials.access_token))
    #from google.appengine.api import urlfetch
    #urlfetch.fetch(revoke_uri)
  #session_store.save_sessions(self.response)

#tailbone_logout_hook = destroy_user

#def create_user(self):
  #session_store = sessions.get_store(request=self.request)
  #session = session_store.get_session()

  #state = self.request.get('state')
  #if state:
    #import json
    #state = json.loads(state)
    #if state.get('secret', False) != session.get('secret', True):
      #raise Exception('Invalid secret.')

    #code = self.request.get('code')
    #from oauth2client.client import credentials_from_code
    #redirect_uri = request.host_url + redirect_path
    #credentials = credentials_from_code(CLIENT_ID, CLIENT_SECRET, scope, code,
        #redirect_uri=redirect_uri)

    #session['credentials'] = credentials.to_json()
    #session['gplus_id'] = credentials.id_token['sub']
    #session_store.save_sessions(self.response)

    #redirect = state.get('continue', None)
    #if redirect:
      #self.redirect(redirect)
      #return True
  #else:
    #session['secret'] = secret()
    #session_store.save_sessions(self.response)

#tailbone_login_hook = create_user

#tailbone_CONFIG = {
  #'webapp2_extras.sessions': {
    #'secret_key': 'my-super-secret-key'
  #}
#}


## Use cloud store instead of blobstore
# tailboneFiles_CLOUDSTORE = False

## Store counts for restful models accessible in HEAD query
# tailboneRestful_METADATA = False

## If specified is a list of tailbone.restful.ScopedModel objects these will be the only ones allowed.
## This is a next level step of model restriction to your db, this replaces validation.json
# from google.appengine.ext import ndb
# from tailbone.restful import ScopedModel
# class MyModel(ScopedModel):
#   stuff = ndb.IntegerProperty()
# tailboneRestful_DEFINED_MODELS = {"mymodel": MyModel}
# tailboneRestful_RESTRICT_TO_DEFINED_MODELS = False

## Protected model names gets overridden by RESTRICTED_MODELS
# tailboneRestful_PROTECTED_MODEL_NAMES = ["(?i)tailbone.*", "custom", "(?i)users"]

## Proxy can only be used for the restricted domains if specified
# tailboneProxy_RESTRICTED_DOMAINS = ["google.com"]

## Cloud store bucket to use default is your application id
# tailboneCloudstore_BUCKET = "mybucketname"

tailboneTurn_RESTRICTED_DOMAINS = ["localhost"]
tailboneTurn_SECRET = "notasecret"

tailboneMesh_ENABLE_TURN = True
# tailboneMesh_ENABLE_WEBSOCKET = True

## Seconds until room expires
# tailboneMesh_ROOM_EXPIRATION = 86400

## Protected site
# tailboneStaticProtected_PASSWORD = "mypassword"
## the base path for the protected site can change to deploy or something else defaults to app
# tailboneStaticProtected_BASE_PATH = "app"

## Custom load balanced compute engine instance
# tailboneCustomCE_STARTUP_SCRIPT = """
# apt-get install build-essential

# curl -O http://nodejs.org/dist/v0.10.15/node-v0.10.15.tar.gz
# tar xvfz node-v0.10.15.tar.gz
# cd node-v0.10.15
# ./configure
# make
# make install
# cd ..
# rm -rf node-v0.10.15
# rm -f node-v0.10.15.tar.gz

# cat >server.js <<EOL
# %s
# EOL

# npm install ws

# node server.js

# """ % (open("client/mywebsocketserver.js").read(),)
