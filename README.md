# Tailbone - Restful AppEngine and then some

The Go Branch is __EXPERIMENTAL__ and not ready for use.

AppEngine is cheap, fast, and awesome. Using it for the first time is sometimes ... well ...
_different_. There are tons of frameworks like Django or others out there that work with AppEngine,
but these days I write almost all my application in javascript with AngularJS, I just need a simple
backend to do its part. The AppEngine frameworks are awesome and for more complex things I recommend
you learn them and use them. All this hopes to do is ease that barrier of use and get people writing
their apps faster without worrying about their backend code.
That said writing more code on your backend is great if you are up to it, I can't recommend Go enough
for doing that, it really is fun.
Anyway, I wrote this for myself in my spare time and hopefully others find it useful too.
It provides a simple restful backend setup for AppEngine so you can write your apps in javascript
via frameworks like AngularJS or Backbone etc and not have to touch any AppEngine code. Or just
using plain javascript and your own xhr calls. All your static resources are automatically served
from client/app.  AppEngine is great at static serving and if you turn on PageSpeed
on AppEngine you get automatic optimization of your images and scripts, as well as other goodies
all for free. It even supports large file uploads and serving via the Google blobstore. One example
use case is drawing an image with canvas via javascript uploading it via ajax and serving variable
sized thumbnails efficiently of that image. That is a simple example in the QUnit tests.

Finally, for added capabilities, there is a javascript library auto served at /tailbone.js which
does additional niceties like bi-directional binding of your model and your backend to a javascript
structure with simplified querying.

- [Status](#status)
- [Special URLS](#special)
    - [/api/(yourModelName)](#models)
    - [/api/users](#users)
    - [Access Control](#access)
    - [/api/files](#files)
    - [/api/events](#events)
- [Taibone.js](#tailbonejs)
    - [Including](#include)
    - [Exported Methods](#exported)
    - [Examples](#example)
- Annotated Source Code
    - [tailbone.py](docs/tailbonepy.html)
    - [tailbone.js](docs/tailbonejs.html)

<a id="status" ></a>
## Status

Just started this is a personal pet project just made out of past experiences and a desire for my
own use though I hope others will find it useful too. Most things are complete and
working with a few rough edges. Also working on a go branch with the same api.
If you want to contribute please add a test for any fix or feature.
Tests can be run by calling ./tailbone/util test to run with the python stubby calls.
For the testing of js code you need to start the dev server by running 'dev_appserver.py .' and
browsing to http://localhost:8080/\_test. These are QUnit javascript tests and should be the
same in either go, python or any future language to support consistency of
any implementation of the api.


<a id="starting" ></a>
## Getting Started

So how I get started with tailbone is.

- First, make sure you have the
  [app engine dev tools](https://developers.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python)
  installed for Python. Note, tailbone uses
  the Python 2.7 version so make sure your default python is at least 2.7.

- Second, clone the repo to the name of your target project

        git clone https://code.google.com/a/google.com/p/tailbone myproject

- Third, create your app in any js framework or static html you want. Tailbone gitignores the client
  folder so anything you put there will be ignored making updating to the latests tailbone as simple
  as git pull and allowing you to have a disconnected git repo of your own to store you application
  code.

        cd myproject
        mkdir -p client/app
        cd client/app
        echo "<html><body>hello world</body></html>" > index.html

- Lastly, start the server like a normal app engine app

        cd ../../..
        dev_appserver.py .
        open http://localhost:8080

For you javascript development I recommend two things [yeoman](http://yeoman.io) for
bootstrapping and installing js libraries and [angularjs](http://angularjs.org) for your MVC
javascript application framework.

<a id="special" ></a>
## Special URLS

<a id="models" ></a>
### Restful models:

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

<a id="access"></a>
### Access Control:

Public private exposure of properties on a model is controlled by capitalization of the first
letter, similar to Go. All models except for "users" have a private owners list which is just a
list of user ids that can access and change the private variables of a model. This is prepopulated
with the person who first creates this model. Only the signed in
user can edit information on their "users" model. I thought about owners vs editors to grant
access rights like most other systems, but thought it out of scope for this first pass trying to
keep everything as simple as possible, so there is just one list add to it or remove from it as you
like.

    var Todo = new tailbone.Model("todos");
    var todo = new Todo();
    todo.Text = "some public text";
    todo.secret = "some secret that only owners can see";

    todo.owners.append("somenewuser"); // now somenewuser can also edit this model and see secret
    todo.$save();


<a id="users" ></a>
### User models:

    /api/users/
      special restful model that can only be edited by the user, authentication via Google Account
    /api/users/me
      Returns the current users information
    /api/login
      logs you in
    /api/logout
      logs you out

Tailbone.js, documented farther down the page, also provides some helpers for logging in and out.
See the QUnit tests for an example. Note, there is also a popup version, but since Chrome
started more agressivly blocking popups being able to create a url that calls a javascript
callback via PostMessage is more useful.

    asyncTest('Login', function() {

      var User = tailbone.User;

      var a = document.createElement('a');
      a.appendChild(document.createTextNode('Login Test'));
      User.logout(function() {
        User.get('me', null, function(d) {
          ok(d.error == 'LoginError', d);
          var link = User.login_popup_url(function() {
            User.get('me', function(d) {
              ok(d.Id !== undefined, d.Id);
              document.body.removeChild(a);
              start();
            });
          });
          a.href = link;
          a.target = '_blank';
        });
      });
      document.body.appendChild(a);
    });


<a id="files" ></a>
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


Upload an image of something drawn with canvas via javascript.

    function toBlob(data_url) {
      var d = atob(data_url.split(',')[1]);
      var b = new Uint8Array(d.length);
      for (var i = 0; i < d.length; i++) {
        b[i] = d.charCodeAt(i);
      }
      return new Blob([b], {type: 'image/png'});
    }

    asyncTest('Upload file', function() {
      var data = new FormData();
      var canvas = document.createElement('canvas');
      document.body.appendChild(canvas);
      var ctx = canvas.getContext('2d');
      ctx.fillRect(0, 0, 100, 100);
      var img = canvas.toDataURL();
      data.append('blob', toBlob(img), 'image_filename');
      document.body.removeChild(canvas);
      $.get('/api/files', function(d) {
        $.ajax({
          type: 'POST',
          url: d.upload_url,
          data: data,
          cache: false,
          contentType: false,
          processData: false,
          success: function(items) {
            var d = items[0];
            ok(d.Id != undefined, 'Id is ' + d.Id);
            ok(d.filename == 'image_filename', 'filename is ' + d.filename);
            ok(d.size == 1616, 'size is ' + d.size);
            ok(d.content_type == 'image/png', 'content type is ' + d.content_type);
            start();
          }
        });
      });
    });


<a id="events" ></a>
### Events:

    /api/events/
      Is a special api used for sending and recieving events across clients.
      This can be used by /tailbone.js which defines functions like:
        tailbone.bind("name", function() { console.log("callback"); });
        tailbone.trigger("name");
        tailbone.unbind("name");


<a id="tailbonejs" ></a>
## Tailbone.js

<a id="include" ></a>
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


<a id="exported" ></a>
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

<a id="example" ></a>
### Examples:

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


