# ![Tailbone](http://workshop.chromeexperiments.com/img/tailbone.gif) Tailbone - Restful AppEngine

### TL;DR

Install helper and dependencies

    brew install google-app-engine go
    go get github.com/doug/tailbone-generator/tailbone

Your new project

    mkdir myproject
    cd myproject
    git init
    tailbone init
    tailbone serve
    open localhost:8080
    # <Ctrl-C> to stop local server
    tailbone deploy master


### Preamble

[App Engine](http://appengine.google.com/) is cheap, fast, and awesome. Using it for the first time 
is sometimes&hellip;well&hellip;different. There are tons of frameworks like 
[Django](https://www.djangoproject.com/) or others out there that work with App Engine,
but these days we write almost all our applications in JavaScript with 
[AngularJS](http://angularjs.org/) or [Backbone.js](http://backbonejs.org/), we just
need a simple backend to do its part. The App Engine server side APIs are great and for more
complex things we recommend you learn them and use them.
All this hopes to do is ease that barrier of use and get people writing
their apps faster without worrying about their backend code.
That said, writing more code on your backend is great if you are up to it,
we can’t recommend [Go](http://golang.org/) enough for doing that, it's a wonderful language.

Anyway, this was written in spare time to fill a need and hopefully others find it useful too.
It provides a simple [RESTful](http://en.wikipedia.org/wiki/Representational_state_transfer) 
backend setup for App Engine so you can write your apps in JavaScript
via frameworks like AngularJS, Backbone, etc. and not have to touch any App Engine code. Or just
using plain JavaScript and your own `xhr` calls. All your static resources are automatically served
from `client/app`. App Engine is great at static serving and if you 
turn on [PageSpeed](https://developers.google.com/appengine/docs/adminconsole/performancesettings)
on App Engine you get automatic optimization of your images and scripts, as well as other goodies
all for free. It even supports large file uploads and serving 
via the [Google Blobstore](https://developers.google.com/appengine/docs/python/blobstore/overview).

### Guiding Principles

- Do as little as possible server side, if it can be done on the client do it there.
- Be as modular as possible so people can mix and match how they choose.
- Only need to edit the app.yaml and appengine_config.py.
- Should work out of the box how most people plan to use it.
- Start with loose security, but be able to harden as you approach launch.
- Be backend implementation agnostic, whether it is Go or Python or something else have a unified javascript interface.

[Style Guide](http://google-styleguide.googlecode.com/svn/trunk/pyguide.html)

- [Status](#status)
- [Getting Started](#getting-started)
- [Modules](#modules)
    - [restful](#restful)
    - [search](#search)
    - [files](#files)
    - [cloudstore](#cloudstore)
    - [geoip](#geoip)
    - [pathrewrite](#pathrewrite)
    - [proxy](#proxy)
    - [clocksync](#clocksync)
    - [mesh](#mesh)
    - [compute_engine](#compute_engine)
    - [static](#static)
    - [test](#test)
- [Extending Tailbone](#extending-tailbone)

## Status

This is a side project made out of past experiences. That being said there are a few rough edges.
Also working on a `Go` branch with the same api. 
If you want to contribute please add a test for any fix or feature before you file a pull request.


## Getting Started

#### Tailbone utility helper:

- Install tailbone

        brew install google-app-engine go
        go get github.com/doug/tailbone-generator/tailbone

- Initialize a new tailbone project

        mkdir myproject
        cd myproject
        git init
        tailbone init

- Start the dev server

        tailbone serve
        open localhost:8080

- Deploy to app engine {version} is your own version name, e.g. 'master'

        tailbone deploy {version}

#### Manual steps to get started:

- First, make sure you have the
  [Google Cloud SDK for Python](https://developers.google.com/cloud/sdk/). Note, tailbone uses
  the [Python 2.7](http://www.python.org/download/releases/2.7/) version so make sure your default python is at least 2.7.

- Second, create a folder and git repo for your new project 

        mkdir myproject
        cd myproject
        git init 

- Third, add tailbone as a submodule to your project

        git submodule add https://github.com/dataarts/tailbone
        git submodule update --init --recursive

- Third, create your app in any js framework or static html you want. As well as copy the app.yaml from the tailbone template.

        cp tailbone/app.template.yaml app.yaml
        mkdir app
        echo "<html><body>hello world</body></html>" > app/index.html

- Lastly, start the server like a normal app engine app, but remember to do so from the tailbone directory.

        dev_appserver.py tailbone
        open http://localhost:8080

__N.B:__ For you javascript development we recommend two things [yeoman](http://yeoman.io) for
bootstrapping and installing js libraries and [angularjs](http://angularjs.org) for your MVC
javascript application framework.

## Modules

## restful

#### Resources:

    POST /api/{modelname}/
      Creates an object.

    PUT or POST /api/{modelname}/{id}
      Updates an object, does a complete overwrite of the properites. This does not do a partial patch.

    GET /api/{modelname}/{id}
      Get a specific object.

    GET /api/{modelname}/?filter={propertyname==somevalue}&order={propertyname}&projection={propertyname1,propertyname2}
      Query a type.

Any `GET` request can take an optional list of properties to return, the query will use those to make a projection query which will only return those properties from the model. The format of the projection is a comma seperated list of properties: `projection=propertyname1,propertyname2,propertyname3`

#### Extending restful

In `appengine_config.py` in your root directory copied from tailbone/appengine_config.template.py

    from google.appengine.ext import ndb
    from tailbone.restful import ScopedModel
    class MyModel(ScopedModel):
      stuff = ndb.FloatProperty()

    tailbone_restful_DEFINED_MODELS = {"mymodel": MyModel}

This will restrict it so that only `/api/mymodel` will work.

If you want some user defined models plus everything else to work with whatever you give it you can also specify.

    tailbone_restful_RESTRICT_TO_DEFINED_MODELS = False

__N.B:__
+ non indexed properties (such as large text or binary fields cannot be given as a
projected property).
+ if owners is not listed as one of the projected properties then only public properties
will be returned, because owners is needed to check ownership.

All restful models have three special properties:
+ `Id`: a public id for the model
+ `owners`: a private list of user ids which represent the owners for this model. By default this includes the user who created it.
+ `viewers`: a private list of user ids which represent the viewers for this model. By default this includes no one.

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

Note: By including `/tailbone.js` this is automatically added.

#### Access Control:

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

#### Validation:

While you have to be authenticated, at the time of this writing you can still write anything to the datastore. This is fantastic for rapid development and changing schemas. However, you might want to be more strict once you deploy your application. In order to help, Tailbone does simple [regex validation](https://github.com/dataarts/tailbone/blob/master/validation.template.json) of all properties.

This is a map of a model name to a series of properties. Anything that is an empty string will effectively bypass validation. Everything else will be parsed as a regex and verified against you and your users requests.

`validation.json` should be created in your root project directory (one level above the tailbone submodule).

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

#### User Models:

    /api/users/
      Special restful model that can only be edited by the user, authentication via Google Account.

    /api/users/me
      Returns the current users information.

    /api/login
      Logs you in.

    /api/logout
      Logs you out.


## search

    /api/search/?q=myquery
      Full text search of models.
      A special api call used for doing full text search of models.

To enable this experimental feature you need to create a [searchable.json](https://github.com/dataarts/tailbone/blob/master/searchable.template.json) which lists which properties on which models are indexed and how they are indexed. Read more about search [here](https://developers.google.com/appengine/docs/python/search/overview). `seachable.json` should be created in your main project directory.

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

## files

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
  $.get('/api/files/create', function(d) {
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

## cloudstore

    GET /api/cloudstore/path/to/your/file.webm
      Fetches files from cloudstore

Fetch files from cloudstore. Useful for serving large files off of cloudstorage without making things fully public add your applications service account as a reader of the file you uploaded to cloud storage.


## geoip

        GET /api/geoip

Get the nearest geoip look up to the users ip address as well as return their remote address.

## pathrewrite

This module makes all paths be returned as app/index.html. Useful when creating an html5 history mode application, that does routing in javascript.

## proxy

        GET /api/proxy?url=http://www.google.com

This module proxies a given url, useful for issues where CORS restricts access to a resource in javascript.
You can restrict which domains are allowed by editing appengine_config.py with 

        tailbone_proxy_RESTRICTED_DOMAINS = ["google.com"]

## clocksync

Syncronize clocks across javascript clients. See [javascript code](https://github.com/dataarts/tailbone/blob/master/tailbone/clocksync/clocksync.js)

## mesh

This module helps create a mesh network for which will use websockets and try to upgrade to webrtc where possible. You will need to enable billing and the compute_engine api since this uses compute_engine to start and maintain TURN servers and Websocket servers.

```html
<script src="/tailbone.js"></script>
```

```javascript
  var mesh = new tailbone.Mesh();
  mesh.bind('connect', function() {
    console.log('mesh connected');
  });
  mesh.bind('test', function(x) {
    console.log('somone sent a test event');
    console.log(x, 'should be 7');
  });
  mesh.trigger('test', 7)
```

## compute_engine

Compute engine is the lower level library for load balancing compute engine instances, see some of the examples in there for how to extend it.

## static

Static content serving. You can change the authorization mechanism for the site in appengine_config.py. Defaults to public.

def my_auth_function(request):
  return True

tailbone_static_authorized = my_auth_function

## test

For the testing you need to start the dev server by running `dev_appserver.py --clear_datastore=yes .` and
browsing to `http://localhost:8080/test/(testname)` for example `http://localhost:8080/test/restful`. 
These are [QUnit](http://qunitjs.com/) JavaScript tests and should be the
same in either go, python or any future language to support consistency of
any implementation of the api. Note, these tests modify the `db`, and will only run locally.

The tests are accessible at /api/test/{module_name} for example /api/test/restful


## Extending Tailbone

Tailbone can be extended by creating a appengine_config.py file in your root directory. Copy it from the template inside tailbone/appengine_config.template.py.
Use this to extend tailbone with any hooks to modify the behavior of tailbone, such as a different authentication mechanism or various module constants. Examples are all commented out in the appengine_config.template.py. See [Python Module Configuration](https://developers.google.com/appengine/docs/python/tools/appengineconfig)

Additionally, you can turn on and off modules by changing what is included in the app.yaml. You can also add your own modules by adding additional incude.yaml paths the app.yaml file.