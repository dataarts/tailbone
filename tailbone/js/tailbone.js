'use strict';

// This is a simple javascript wrapper to make using the restful api provided
// by tailbone easier.  It also includes bi-directional data binding with
// AppEngine and the channel api so that your javascript models upload in
// real time.

window.tailbone = (function(window, document, undefined) {

// We expose a global config object the only use at this point is to
// enable the databinding feature which triggers and fetches updates
// when other people modify one of the models you are querying.
var config = {
  databinding: true
};

// Since all of this is ajax there is a simple wrapper around $.ajax.
// If you don't have jQuery already on your site you will need to install
// it or provide your own global function that has the same api and bind
// it to $.ajax (for example you could use zepto.js but since
// jQuery is cached in most browsers I would just point
// to the google jQuery CDN)
var http = {};
function errorWrapper(fn) {
  if (fn) {
    return function(jqXHR, textStatus, errorThrown) {
      var data;
      try {
        data = JSON.parse(jqXHR.responseText);
      } catch (e) { }
      fn(data, textStatus, jqXHR, errorThrown);
    }
  }
}
http.GET = function(url, load, error) {
  $.ajax({
    type: 'GET',
    url: url,
    success: load,
    error: errorWrapper(error),
    dataType: 'json'
  });
};
http.POST = function(url, data, load, error) {
  $.ajax({
    type: 'POST',
    url: url,
    data: JSON.stringify(data),
    success: load,
    error: errorWrapper(error),
    dataType: 'json',
    contentType: 'application/json'
  });
};
http.DELETE = function(url, load, error) {
  $.ajax({
    type: 'DELETE',
    url: url,
    success: load,
    error: errorWrapper(error),
    dataType: 'json'
  });
};



// Quering and Filtering
// ---------------------
// These are some useful helper functions for constructing queries, although you
// probably won't have to use these directly, see the query section below.

function FILTER(name, opsymbol, value) {
  return [name, opsymbol, value];
}

function ORDER(name) {
  return name;
}

function AND() {
  var f = ['AND'];
  for (var i = 0; i < arguments.length; i++) {
    f.push(arguments[i]);
  }
  return f;
}

function OR() {
  var f = ['OR'];
  for (var i = 0; i < arguments.length; i++) {
    f.push(arguments[i]);
  }
  return f;
}


// This helps construct a model type which can be queried and created.
var ModelFactory = function(type, opt_schema) {
  var ignored_prefixes = ['_', '$'];


  // Model
  // -----
  // This is a model class for the particular type. This allows you to work with
  // your models directly in javascript and has several built in functions to
  // save them back to the server.
  var Model = function() {
  };

  // Get a model by its id.
  Model.get = function(id, opt_callback, opt_error) {
    var m = new Model();
    m.Id = id;
    m.$update(opt_callback, opt_error);
    return m;
  };

  // Query generates a iterator for a query object. Queries inherit from the
  // native array type so all the ES5 iterators work on query objects, for
  // example:
  //
  //     var Todo = new tailbone.Model("todos");
  //     Todo.query(function(todos) {
  //       todos.forEach(function(v,i) {
  //         console.log(v,i);
  //       });
  //     });
  Model.query = function(opt_callback) {
    var query = new Query();
    // xhr query for collection with timeout to allow for chaining.
    //
    //     var results = Todo.query().filter("text =", "sample")
    setTimeout(function() {
      query.fetch(opt_callback);
    }, 0);
    // Bind to watch for changes to this model by others on the server.
    if (config.databinding) {
      tailbone.bind(type, function() { query.fetch() });
    }
    return query;
  };

  // Helper function to serialize a model and strip any properties that match
  // the set of ignored prefixes or are of an unsupported type such as a
  // function.
  function serializeModel(model) {
    var obj = {};
    for (var member in model) {
      if (ignored_prefixes.indexOf(member[0]) < 0) {
        obj[member] = model[member];
      }
    }
    return obj;
  };

  // Save the model to the server.
  Model.prototype.$save = function(opt_callback, opt_error) {
    var model = this;
    http.POST('/api/' + type + '/', serializeModel(this), function(data) {
      for (var k in data) {
        model[k] = data[k];
      }
      var fn = opt_callback || model.onchange;
      if (fn) {
        fn(model);
      }
      if (config.databinding) {
        tailbone.trigger(type);
      }
    }, opt_error);
  };

  // Delete the model.
  Model.prototype.$delete = function(opt_callback, opt_error) {
    var model = this;
    http.DELETE('/api/' + type + '/' + this.Id, function() {
      var fn = opt_callback || model.onchange;
      if (fn) {
        fn();
      }
      if (config.databinding) {
        tailbone.trigger(type);
      }
    }, opt_error);
  };

  // Update the model by fetching its latest value and overwriting the current
  // object.
  Model.prototype.$update = function(opt_callback, opt_error) {
    var model = this;
    http.GET('/api/' + type + '/' + this.Id, function(data) {
      for (var k in data) {
        model[k] = data[k];
      }
      var fn = opt_callback || model.onchange;
      if (fn) {
        fn(model);
      }
    }, opt_error);
  };


  // Query
  // -----
  // Query is an iterable collection of a Model.
  var Query = function() {
    var query = [],
        _filter = [],
        _order = [],
        _page_size = 100,
        _more = false,
        _dirty = false;

    // Provide a projection of desired properties to the query
    query.projection = [];

    // the onchange callback
    query.onchange = undefined;

    query.next = function() {
      return true;
    };

    query.previous = function() {
      return true;
    };

    query.__defineGetter__('more', function() { return _more; });

    query.__defineGetter__('page_size',
        function() { return _page_size; });
    query.__defineSetter__('page_size',
        function(page_size) {
          _page_size = page_size;
          _dirty = true;
        });

    // Filter the query results. This can either be a constructed filter using one
    // of the provided functions like
    // AND(FILTER("name","=","value"), FILTER("other","=","value")). Or you can
    // construct a filter in place with the shorthand. filter("name","=","value")
    // or filter("name =", "value")
    query.filter = function() {
      var filter;
      switch (arguments.length) {
        case 1:
          filter = arguments[0];
          break;
        case 2:
          filter = FILTER.apply(this,
              arguments[0].split(' ').concat(arguments[1]));
          break;
        case 3:
          filter = FILTER.apply(this, arguments);
          break;
        default:
          throw Error('Undefined FILTER format.');
      }
      if (_filter.length == 0) {
        _filter = ['AND'];
      }
      _filter.push(filter);
      return this;
    };

    // Order the query results. add a - in front of the name to make it sort
    // descending.
    query.order = function(name) {
      _order.push(ORDER(name));
      return this;
    };

    // Simple serialization and jsonification of the query so it can be passed to
    // the server.
    query.serialize = function() {
      return JSON.stringify({
        filter: _filter,
        order: _order,
        projection: this.projection,
        page_size: _page_size
      });
    };

    // Actually fetches and updates the results in the query. This happens
    // automatically on a query so you shouldn't need this unless you want to
    // update the results this will fetch and update the current results.
    query.fetch = function(opt_callback) {
      var query = this;
      function callback(data) {
        query.splice(0, query.length);
        query.push.apply(query, data);
        var fn = opt_callback || query.onchange;
        if (fn) {
          fn(query);
        }
      }
      http.GET('/api/' + type + '/?params=' + this.serialize(), callback);
    };

    return query;
  };



  return Model;
};

// User is a built in model that is constructed like a normal model but has some
// additional functionality built in.
var User = new ModelFactory('users');

function authorizeCallback(opt_callback) {

  function processToken(callback) {
    return function(message) {
      if (message.data.type != 'Login') {
        return;
      }
      var localhost = false;
      if (message.origin.substr(0, 17) == 'http://localhost:') {
        localhost = true;
      }
      if (!localhost && message.origin !== window.location.origin) {
        throw new Error('Origin does not match.');
      } else {
        removeEventListener('message', process, false);
        if (callback) {
          callback(message.data.payload);
        }
      }
    };
  }

  var process = processToken(opt_callback);
  addEventListener('message', process, false);

}

// Constructs a login url.
User.logout_url = function(redirect_url) {
  return '/api/login?url=' + (redirect_url || '/');
};

User.login_url = function(redirect_url) {
  return '/api/login?url=' + (redirect_url || '/');
};

// Constructs a login url use this with target _blank and setting a link on your
// site for the best experience on most devices.
User.login_callback_url = function(opt_callback) {
  authorizeCallback(opt_callback);
  return User.login_url('/api/login.html');
};

User.logout = function(opt_callback) {
  http.GET('/api/logout?url=/api/users/me', null, opt_callback);
};

// Does the login with a popup in javascript. There is a potential problem with
// this on browsers that don't support popups like some latest chrome builds and
// most mobile devices.
User.login = function(opt_callback) {
  var x, y;
  if (window.screen.width) {
    x = window.screenX + window.screen.width / 2.0;
    y = window.screenY + window.screen.height / 2.0;
  }

  var pos = {
    x: x,
    y: y,
    width: 1100,
    height: 600
  };

  var prop = 'menubar=0, resizable=0, location=0, toolbar=0, ' +
    'status=0, scrollbars=1, titlebar=0, left=' +
    (pos.x - (pos.width / 2.0)) + ', top=' +
    (pos.y - (pos.height / 2.0)) + ', width=' +
    pos.width + ', height=' + pos.height;

  window.open(User.login_callback_url(opt_callback), 'Auth', prop);
};


// Event API
// ---------
// This is some code you should have to care about that does the event binding.
// This exposes simple functions like bind, unbind, and trigger that will send
// messages to all subscribed other users currently on the site. This is what
// does the bidirectional databinding. I exposes it so you can use it for other
// purposes as well.
var CONNECTED = false;
var CONNECTING = false;
var BACKOFF = 1;

var event_map = {};
var queue = [];
var socket;
var client_id = parseInt(Date.now() / Math.random());

function onOpen() {
  CONNECTED = true;
  BACKOFF = 1;
  for (var i = 0, l = queue.length; i < l; i++) {
    queue[i].call(this);
  }
  queue = [];
}

function rebind() {
  var event_bindings = [];
  for (var name in event_map) {
    for (var fn in event_map[name]) {
      event_bindings.push([name, fn]);
    }
  }
  event_map = {};
  for (var i = 0, l = event_bindings.length; i < l; i++) {
    ifConnected(bind, event_bindings[i][0], event_bindings[i][1]);
  }
}

function onClose() {
  CONNECTED = false;
  CONNECTING = false;
  rebind();
}

// TODO: try reconnecting with backoff or alert system of lack of capability.
function onError() {
  if (console) {
    console.warn('Channel not connectable.');
  }
}

function onMessage(msg) {
  var data = JSON.parse(msg.data);
  if (data.reboot) {
    socket.close();
    return;
  }
  var fns = event_map[data.name];
  if (fns && fns.length > 0) {
    for (var i = 0, l = fns.length; i < l; i++) {
      fns[i].call(fns[i], data.payload);
    }
  }
}

function connect(callback) {
  if (callback) queue.push(callback);
  if (!CONNECTING) {
    http.POST('/api/events/',
        {'method': 'token', 'client_id': client_id},
        function(resp) {
          var channel = new goog.appengine.Channel(resp.token);
          socket = channel.open();
          socket.onopen = onOpen;
          socket.onmessage = onMessage;
          socket.onclose = onClose;
          socket.onerror = onError;
        }
    );
  } else {
    CONNECTING = true;
  }
}

function ifConnected(fn, arg1, arg2) {
  var _this = this;
  if (CONNECTED) {
    fn.call(_this, arg1, arg2);
  } else {
    connect(function() {fn.call(_this, arg1, arg2);});
  }
}

function errorHandler(msg) {
  if (msg && msg.error && console) {
    console.warn(msg.error);
  }
}

function trigger(name, payload) {
  http.POST('/api/events/',
      {'method': 'trigger',
       'client_id': client_id,
       'name': name, 'payload': payload},
       null,
       errorHandler);
}

function bind(name, fn) {
  event_map[name] = event_map[name] || [];
  event_map[name].push(fn);
  http.POST('/api/events/',
      {'method': 'bind',
       'client_id': client_id,
       'name': name},
       null,
       errorHandler);
}

function unbind(name, fn) {
  if (name) {
    if (fn) {
      var index = event_map[name].indexOf(fn);
      if (index < 0) {
        throw new Error('No matching function exists.');
      } else {
        delete event_map[name][index];
      }
    } else {
      delete event_map[name];
    }
  } else {
    event_map = {};
  }
  http.POST('/api/events/',
      {'method': 'unbind',
       'client_id': client_id, 'name': name},
      null,
      errorHandler);
}


// Exports
// -------
return {
  Model: ModelFactory,
  User: User,
  FILTER: FILTER,
  ORDER: ORDER,
  AND: AND,
  OR: OR,
  trigger: function(name, payload) { ifConnected(trigger, name, payload); },
  bind: function(name, fn) { ifConnected(bind, name, fn); },
  unbind: function(name, fn) { ifConnected(unbind, name, fn); },
  config: config
};

})(this, this.document);
