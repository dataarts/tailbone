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

# tailboneTurn_RESTIRCTED_DOMAINS = ["localhost"]
# tailboneTurn_SECRET = "notasecret"

# tailboneMesh_ENABLE_TURN = True
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