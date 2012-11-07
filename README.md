# Automatic RESTful backend for AppEngine

A simple restful backend setup for app engine so you can write your apps in javascript via
frameworks like AngularJS or Backbone etc and not have to touch any app engine code. Or just
using plain javascript and your own xhr calls.

Also, for added capabilities, there is a javascript library auto served at /tailbone.js which does
additional niceties like bi-directional binding of your model and your backend to a javascript
structure with simplified queries.

## Status

Just started. Most things are complete and working a few rough edges. Also working on a go branch
with the same api. If you want to contribute please add a test for any fix or feature. Test can be
run by calling ./tailbone/util test to run with the python stubby calls.
For the testing of js code you need to start the dev server by running 'dev_appserver.py .' and
browsing to http://localhost:8080/_test

## Special URLS

### RESTful models:

    POST /api/{modelname}/
      creates an object
    PUT or POST /api/{modelname}/{id}
      updates an object, does a complete overwrite of the properites not a partial patch
    GET /api/{modelname}/{id}
      Get a specific object
    GET /api/{modelname}/?filter={propertyname==somevalue}&order={propertyname}&projection={propertyname1,propertyname2}
      Query a type
    Any GET request can take an optional list of properties to return, the query will use those
    to make a projection query which will only return those properties from the model.
    The format of the projection is a comma seperated list of properties.
    projection=propertyname1,propertyname2,propertyname3
    Note: non indexed properties (such as large text or binary fields cannot be given as a
    projected property).
    Note: if owners is not listed as one of the projected properties then only public properties
    will be returned, because owners is needed to check ownership.

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
      returns
        {"upload_url": "http://some-special-upload-url"}
    GET /api/files/{id}
      returns the actual uploaded file
      if the file was an image it the POST call will return a special url called "image_url" which
      should be used as the url for any images, it will not only serve faster, but it can take
      additional parameters to automatically crop and produce thumbnail images. Do so by appending
      =sXX to the end of the url. For example =s200 will return a 200 sized image with the original
      aspect ratio. =s200-c will return a cropped 200 sized image.
      RETURNS
        Actual binary file
    POST {special url returned from GET /api/files/}
      uploads the form data to blobstore
      All files are public but obscured
      returns the files names, info and their ids
      also and image_url if the uploaded file was an image/(png|jpeg|jpg|webp|gif|bmp|tiff|ico)
      RETURNS
        [
          {
          "filename": filename,
          "content_type": content_type,
          "creation": creation-date,
          "size": file-size,
          "image_url": optional-image-url-if-content_type-is-image
          },
          ...
        ]
    DELETE /api/files/{id}
      deletes a file from blobstore
      note there is no put to update an id you must always create a new one and delete the old
      yourself

### Events:

    /api/events/
      Is a special api used for sending and recieving events across clients.
      This can be used by /tailbone.js which defines functions like:
        tailbone.bind("name", function() { console.log("callback"); });
        tailbone.trigger("name");
        tailbone.unbind("name");


## Tailbone.js

### How to include:

    to use tailbone.js please include the following in your html
    if you don't want to use jquery just define $.ajax yourself somehow somewhere
    <script src="//ajax.googleapis.com/ajax/libs/jquery/1.8.2/jquery.min.js"></script>
    <script src="/_ah/channel/jsapi" type="text/javascript" charset="utf-8"></script>
    <script src="/tailbone.js" type="text/javascript" charset="utf-8"></script>

    to support older browsers also include this before the other two scripts
    <!--[if lt IE 7]>
        <p class="chromeframe">You are using an outdated browser. <a href="http://browsehappy.com/">Upgrade your browser today</a> or <a href="http://www.google.com/chromeframe/?redirect=true">install Google Chrome Frame</a> to better experience this site.</p>
    <![endif]-->
    <!--[if lt IE 9]>
        <script src="//cdnjs.cloudflare.com/ajax/libs/es5-shim/1.2.4/es5-shim.min.js"></script>
        <script src="//cdnjs.cloudflare.com/ajax/libs/json3/3.2.4/json3.min.js"></script>
    <![endif]-->


### Exported methods:

    Model: ModelFactory that creates a new model type,
    User: Automatically created special model for users info
    FILTER: create a filter FILTER,
    ORDER: create an order ORDER,
    AND: AND of two or more filters,
    OR: OR of two or more filters,
    trigger: trigger an event,
    bind: bind a js function by name ,
    unbind: unbind a js function by name,

### Example:

    var Todo = new tailbone.Model("todos");
    var todos = Todo.query().filter("text =", "Go to store").order("-date");

    var todo = new Todo();
    todo.text = "Go to store";
    todo.date = Date.now()
    todo.$save();

    todos.onchange = function() {
      todos.forEach(function(item, idx) {
        console.log(idx, item);
      });
    };


