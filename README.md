# ![Tailbone](http://workshop.chromeexperiments.com/img/tailbone.gif) Tailbone - Restful App Engine and then some

### Preamble

[App Engine](http://appengine.google.com/) is cheap, fast, and awesome. Using it for the first time is sometimes&hellip;well&hellip;different. There are tons of frameworks like [Django](https://www.djangoproject.com/) or others out there that work with App Engine,
but these days we write almost all our applications in JavaScript with [AngularJS](http://angularjs.org/) or [Backbone.js](http://backbonejs.org/), we just
need a simple backend to do its part. The App Engine server side APIs are great and for more
complex things we recommend you learn them and use them.
All this hopes to do is ease that barrier of use and get people writing
their apps faster without worrying about their backend code.
That said, writing more code on your backend is great if you are up to it,
we can’t recommend [Go](http://golang.org/) enough for doing that, it's a wonderful language.

Anyway, this was written in spare time to fill a need and hopefully others find it useful too.
It provides a simple [RESTful](http://en.wikipedia.org/wiki/Representational_state_transfer) backend setup for App Engine so you can write your apps in JavaScript
via frameworks like AngularJS, Backbone, etc. and not have to touch any App Engine code. Or just
using plain JavaScript and your own `xhr` calls. All your static resources are automatically served
from `client/app`. App Engine is great at static serving and if you turn on [PageSpeed](https://developers.google.com/appengine/docs/adminconsole/performancesettings)
on App Engine you get automatic optimization of your images and scripts, as well as other goodies
all for free. It even supports large file uploads and serving via the [Google Blobstore](https://developers.google.com/appengine/docs/python/blobstore/overview).

### An Overview of an Example Use Case

Draw an image with `canvas` via JavaScript. Upload it via `ajax` and serve variable
sized thumbnails efficiently of that image. There is a simple example in the [QUnit tests](https://github.com/dataarts/tailbone/blob/master/tailbone/js/test_restful.html).
It also has experimental support for model validation and full text search.

### A Word About Tailbone.js

Finally, for added capabilities, there is a JavaScript library served up which
does additional niceties like bi-directional binding of your model and your backend to a JavaScript
structure with simplified querying. The JavaScript library is pretty alpha don’t think we would
necessarily rely on that part just yet.

- [Status](#status)
- [Special URLS](#special-urls)
    - [/api/(yourModelName)](#restful-models)
    - [Access Control](#access-control)
    - [Validation](#validation)
    - [/api/users](#user-models)
    - [/api/files](#large-files)
    - [/api/events](#events)
    - [/api/search](#search)
- [Taibone.js](#tailbonejs)
    - [Including](#how-to-include)
    - [Exported Methods](#exported-methods)
    - [Examples](#examples)
- Annotated Source Code
    - [tailbone.py](docs/tailbonepy.html)
    - [tailbone.js](docs/tailbonejs.html)

## Status

This is a side project made out of past experiences. That being said there are a few rough edges.
Also working on a `Go` branch with the same api. If you want to contribute please add a test for any fix or feature before you file a pull request.
Tests can be run by calling ./tailbone/util test to run with the python stubby calls.
For the testing of js code you need to start the dev server by running `dev_appserver.py .` and
browsing to `http://localhost:8080/_test`. These are [QUnit](http://qunitjs.com/) JavaScript tests and should be the
same in either go, python or any future language to support consistency of
any implementation of the api. Note, these tests modify the `db`, and can only be run locally.


## Getting Started

How to get started:

- First, make sure you have the
  [app engine dev tools](https://developers.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python)
  installed for Python. Note, tailbone uses
  the [Python 2.7](http://www.python.org/download/releases/2.7/) version so make sure your default python is at least 2.7.

- Second, clone the repo to the name of your target project

        git clone https://github.com/doug/tailbone.git myproject

    Add this to your dot files `alias tailbone="git clone https://github.com/doug/tailbone.git"`
    so you can just type `tailbone myproject`

- Third, create your app in any js framework or static html you want. Tailbone `gitignores` the client
  folder so anything you put there will be ignored making updating to the latests tailbone as simple
  as git pull. This allows you to have a disconnected git repo of your own to store you application
  code.

        cd myproject
        mkdir -p client/app
        cd client/app
        echo "<html><body>hello world</body></html>" > index.html

- Lastly, start the server like a normal app engine app

        cd ../../..
        dev_appserver.py .
        open http://localhost:8080

__N.B:__ For you javascript development we recommend two things [yeoman](http://yeoman.io) for
bootstrapping and installing js libraries and [angularjs](http://angularjs.org) for your MVC
javascript application framework.

## Special URLS

### RESTful Models:

    POST /api/{modelname}/
      Creates an object.

    PUT or POST /api/{modelname}/{id}
      Updates an object, does a complete overwrite of the properites. This does not do a partial patch.

    GET /api/{modelname}/{id}
      Get a specific object.

    GET /api/{modelname}/?filter={propertyname==somevalue}&order={propertyname}&projection={propertyname1,propertyname2}
      Query a type.

Any `GET` request can take an optional list of properties to return, the query will use those to make a projection query which will only return those properties from the model. The format of the projection is a comma seperated list of properties: `projection=propertyname1,propertyname2,propertyname3`

__N.B:__
+ non indexed properties (such as large text or binary fields cannot be given as a
projected property).
+ if owners is not listed as one of the projected properties then only public properties
will be returned, because owners is needed to check ownership.

All restful models have two special properties:
+ `Id`: a public id for the model
+ `owners`: a private list of user ids which represent the owners for this model. By default this includes the user who created it.

Special types include:
+ __Geolocations__: this occurs when you serialize your json data as `{"lat": NUMBER, "lon": NUMBER}`
+ __Timestamps__: this is in [ISO 8601 DateTime](http://en.wikipedia.org/wiki/ISO_8601) format, this is the same style JSON supports when given a new [`Date()`](http://kangax.github.com/es5-compat-table/#Date.prototype.toISOString) in ECMAScript 5.

To extend the loading of a date strings into native javascript Date format try something like:

```javascript
var reISO = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}(?:\.\d*)?)Z$/;

JSON._parse = JSON.parse;
JSON.parse = function(json) {
  return JSON._parse(json, function(key, value) {
    if (typeof value === 'string') {
      if (reISO.exec(value)) {
        return new Date(value);
      }
    }
    return value;
  });
};
```

### Access Control:

Public private exposure of properties on a model is controlled by capitalization of the first letter, similar to `Go`. All models except for `users` have a private owners list which is just a list of user ids that can access and change the private variables of a model. This is prepopulated with the person who first creates this model. __Only the signed in
user can edit information on their `users` model__. We thought about owners vs. editors to grant access rights like many other systems, but thought it out of scope for this first pass. This is about rapid prototyping.

```javascript
$.ajax({
  url: "/api/todos/",
  method: "POST",
  data: {
    Text: "some public text",
    secret: "some secret that only owners can see"
  }
})
```

### Validation:

While you have to be authenticated, at the time of this writing you can still write anything to the datastore. This is fantastic for rapid development and changing schemas. However, you might want to be more strict once you deploy your application. In order to help, Tailbone does simple [regex validation](https://github.com/dataarts/tailbone/blob/master/validation.template.json) of all properties.

This is a map of a model name to a series of properties. Anything that is an empty string will effectively bypass validation. Everything else will be parsed as a regex and verified against you and your users requests.

__N.B:__ This is still experimental and not full vetted. Don’t hesitate to file any issues when you find bugs. Finally, as in the example below you will need to escape any `'`’s in your regular expression.

```javascript
{
  "todos": {
    "skipvalidation": "",
    "anything": ".*",
    "shortstring": "^.{3,30}$",
    "integer": "^[-]?[0-9]+$",
    "float": "^[-]?([0-9]*\\.[0-9]+|[0-9]+)$",
    "timestamp": "^[0-9]+$",
    "object": "^\\{.*\\}$",
    "objectdeep": {
      "anything": ".*",
      "skipvalidation": "",
      "integer": "^[-]?[0-9]+$"
    },
    "list": "^\\[.*\\]$"
  },
  "documents_with_anything": ""
}
```

This validates a bunch of things on `/api/todos/` and lets anything through on `/api/documents_with_anything`. No other models will be admitted to your database.

### User Models:

    /api/users/
      Special restful model that can only be edited by the user, authentication via Google Account.

    /api/users/me
      Returns the current users information.

    /api/login
      Logs you in.

    /api/logout
      Logs you out.

Tailbone.js, documented [farther down the page](https://github.com/dataarts/tailbone#tailbonejs), also provides some helpers for logging in and out. See the QUnit tests for an example. 
Note, there is also a popup version, but since Chrome started more aggressively blocking popups being able to create a url that calls a javascript callback via [PostMessage](https://developer.mozilla.org/en-US/docs/DOM/window.postMessage) is more useful.

```javascript
asyncTest('Login', function() {

  var User = tailbone.User;

  var a = document.createElement('a');
  a.appendChild(document.createTextNode('Login Test'));
  User.logout(function() {
    User.get('me', null, function(d) {
      ok(d.error == 'LoginError', d);
      var link = User.login_callback_url(function() {
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
```


### Large Files:

    GET /api/files/create
      Call prior to uploading files. Returns an object with an "upload_url" property. POST files there.

    GET /api/files/
      List all blob info objects. This can only be accessed by administrators.

    GET /api/files/{id}
      Returns the actual uploaded file. If file is an image there will be an "image_url" instead of the file.

    POST {special url returned from GET /api/files/}
      Uploads form data to Blobstore. All files are public, but obscured. Returns the files names, info, and their ids.

    DELETE /api/files/{id}
      Deletes a file from blobstore. This can only be done by administrators.

__N.B:__ There is no `PUT` to update a file. You must always create a new one and delete the old one yourself.

#### Image Saving and Serving with `/api/files`

When the file you `POST`ed is an image that call will return a special url called `image_url`. This should be used as the url for any images, it will not only serve faster, but it can take additional parameters to automatically crop and produce thumbnail images. Do so by appending `=sXX` to the end of the url. __E.G:__ `=s200` will return a `200` sized image with the original aspect ratio. `=s200-c` will return a cropped `200` sized image.

These filetypes are considered images:
+ `png`
+ `jpeg`
+ `jpg`
+ `webp`
+ `gif`
+ `bmp`
+ `tiff`
+ `ico`

#### Relevant Information Attached to Large Files

When you `POST` files to the `upload_url` you’ve requested the response will contain a list of objects. Each object represents the file that you `POST`ed. Each object will have additional information outlined below:

```javascript
[
  {
  "Id": file_id,
  "filename": filename,
  "content_type": content_type,
  "creation": creation-date,
  "size": file-size,
  "image_url": optional-image-url-if-content_type-is-image
  },
  ...
]
```

__N.B:__ The `image_url` is only present if the file `POST`ed is an image. In addition the `POST` is currently the only scenario where you can receive meta-information about the file uploaded. So be sure to keep the `file_id` for retrieval later!

#### Upload an image of something drawn with canvas via JavaScript.

```javascript
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
```

### Events:

    /api/events/
      A special api call used for sending and receiving events across clients.

One way to leverage this is by using Tailbone.js. It implements through event functions:

    tailbone.bind("name", function() { console.log("callback"); });
    tailbone.trigger("name");
    tailbone.unbind("name");

### Search:

    /api/search/?q=myquery
      Full text search of models.
      A special api call used for doing full text search of models.

To enable this experimental feature you need to create a [searchable.json](https://github.com/dataarts/tailbone/blob/master/searchable.template.json) which lists which properties on which models are indexed and how they are indexed. Read more about search [here](https://developers.google.com/appengine/docs/python/search/overview).

Example searchable.json

```javascript
{
  "todos": {
    "_index": "optional_field_for_name_of_index_default_if_not_defined",
    "item": "TextField",
    "snippet": "HtmlField",
    "slug": "AtomField",
    "value": "NumberField",
    "dayof": "DateField",
    "place": "GeoField"
  }
}
```

## Tailbone.js

### How to include:

In order to use Tailbone.js include the following in your html. If you don’t want to use jquery then you must define `$.ajax` yourself prior to importing Tailbone.js:

```html
<script src="//ajax.googleapis.com/ajax/libs/jquery/1.8.2/jquery.min.js"></script>
<script src="/_ah/channel/jsapi" type="text/javascript" charset="utf-8"></script>
<script src="/tailbone.json.js" type="text/javascript" charset="utf-8"></script>
<script src="/tailbone.models.js" type="text/javascript" charset="utf-8"></script>
```

In order to support older browsers also include this before the other two scripts:

```html
<!--[if lt IE 7]>
    <p class="chromeframe">You are using an outdated browser. <a href="http://browsehappy.com/">Upgrade your browser today</a> or <a href="http://www.google.com/chromeframe/?redirect=true">install Google Chrome Frame</a> to better experience this site.</p>
<![endif]-->
<!--[if lt IE 9]>
    <script src="//cdnjs.cloudflare.com/ajax/libs/es5-shim/1.2.4/es5-shim.min.js"></script>
    <script src="//cdnjs.cloudflare.com/ajax/libs/json3/3.2.4/json3.min.js"></script>
<![endif]-->
```


### Exported methods:

+ `Model`: `ModelFactory` that creates a new model type.
+ `User`: Automatically created special model for user’s info.
+ `FILTER`: Create a filter `FILTER`.
+ `ORDER`: Create an order `ORDER`.
+ `AND`: `AND` of two or more filters.
+ `OR`: `OR` of two or more filters.
+ `trigger`: trigger an event.
+ `bind`: bind a JavaScript function by name.
+ `unbind`: unbind a JavaScript function by name.

### Examples:

```javascript
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
```

