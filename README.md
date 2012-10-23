# Automatic RESTful backend for AppEngine

A simple restful backend setup for app engine so you can write your apps in javascript via
frameworks like AngularJS or Backbone etc etc and not have to touch any app engine code. Or just
using plain javascript and your own xhr calls.

Also, for added capabilities, there is a javascript library auto served at /tailbone.js which does
additional niceties like bi-directional binding of your model and your backend to a javascript
structure etc etc.

## Special URLS

### RESTful models:

    POST /api/{modelname}/
      creates an object
    PUT or POST /api/{modelname}/{id}
      updates an object, does a complete overwrite of the properites not a partial patch
    GET /api/{modelname}/{id}
      Get a specific object
    GET /api/{modelname}/?filter={propertyname==somevalue}&order={propertyname}
      Query a type
    Any GET request can take an optional projection map which will only return those properties
    from the model. The format of the projection map is a comma seperated list of properties.
    properties=propertyname1,propertyname2,propertyname3
    Note: non indexed properties (such as large text or binary fields cannot be given as a
    projected property).

    All restful models have two special properties:
    "Id" which is a public id for the model
    "owners" which is a private list of the user ids of owners for this model, which by default just
    includes the user who creates it.

### User models:

    /api/users/
      special restful model that can only be edited by the user, authentication via Google Account
    /api/users/me
      Returns the current users information
    /api/login
      logs you in
    /api/logout
      logs you out

### Large files:

    GET /api/files/
      Must be called first to get the special upload url that files can be posted to for storage.
    GET /api/files/{id}
      returns the actual uploaded file
      if the file was an image it the POST call will return a special url called "image_url" which
      should be used as the url for any images, it will not only serve faster, but it can take
      additional parameters to automatically crop and produce thumbnail images. Do so by appending
      =sXX to the end of the url. For example =s200 will return a 200 sized image with the original
      aspect ratio. =s200-c will return a cropped 200 sized image.
    POST {special url returned from GET /api/files/}
      uploads the form data to blobstore
      All files are public but obscured
      returns the files names, info and their ids
      also and image_url if the uploaded file was an image/(png|jpeg|jpg|webp|gif|bmp|tiff|ico)
    DELETE /api/files/{id}
      deletes a file from blobstore
      note there is no put to update an id you must always create a new one and delete the old
      yourself

### Events:

    /api/events/
      Is a special api used for sending and recieving events across clients.
      This can be used by the /tailbone.js which defines functions like:
        tailbone.bind("name", function() { console.log("callback"); });
        tailbone.trigger("name");
        tailbone.unbind("name");

### Tailbone.js

    to use tailbone.js please include the following in your <head>
    <script src="/_ah/channel/jsapi" type="text/javascript" charset="utf-8"></script>
    <script src="/tailbone.js" type="text/javascript" charset="utf-8"></script>

