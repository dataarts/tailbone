'use strict';

/*
 * Bi-Directional data binding with AppEngine and the channel api
 */

window.tailbone = (function(window, document, undefined) {

// Do checks for minimum requirements
if (!XMLHttpRequest || !JSON || !Array.prototype.indexOf || !Array.prototype.forEach) {
  throw Error('Browser does not support the minimum requirements of ' +
        'XMLHttpRequest, JSON, Ecmascript 5 array functions' +
        '. Try adding a polyfill to provide shims to the functions you need.');
}

function http(o) {
  // method, url, data, success, error, progress) {
  var r = new XMLHttpRequest();
  var async = o.async == undefined ? true : o.async;
  r.open(o.method || 'GET', o.url, async);
  if (o.progress) {
    r.onprogress = function(e) {
      if (e.lengthComputable) {
        var percentComplete = (e.loaded / e.total);
        o.progress(percentComplete, e, r);
      }
    };
  }
  function response() {
    switch (r.getResponseHeader('Content-Type')) {
      case 'application/json':
        return JSON.parse(r.responseText);
      default:
        return r.responseText;
    }
  }
  if (o.load) {
    r.onload = function(e) {
      o.load(response(), e, r);
    };
  }
  if (o.error) {
    r.onerror = function(e) {
      o.error(response(), e, r);
    };
  }
  var data = o.data || null;
  if (data) {
    switch (toString.call(data)) {
      case '[object String]':
        // r.setRequestHeader('Content-Type',
        // 'application/x-www-form-urlencoded');
        // This is already assumed.
        break;
      case '[object FormData]':
        // r.setRequestHeader('Content-Type', 'multipart/form-data');
        // Don't set this because a FormData sets this correctly for you and
        // must set the boundry.
        break;
      default:
        r.setRequestHeader('Content-Type', 'application/json');
        data = JSON.stringify(data);
        break;
    }
  }
  r.send(data);
}

http.GET = function(url, load, error) {
  http({method: 'GET', url: url, load: load, error: error}); };
http.POST = function(url, data, load, error) {
  http({method: 'POST', url: url, data: data, load: load, error: error}); };
http.DELETE = function(url, load, error) {
  http({method: 'DELETE', url: url, load: load, error: error}); };

/////////////////////////
// Events via Channel API
/////////////////////////

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

function onError() {
  // TODO: try reconnecting with backoff or alert system of lack of capability.
  if (console) {
    console.warn('Channel not connectable.');
  }
}

function onMessage(msg) {
  var data = JSON.parse(msg.data);
  if (data.reboot) {
    // close everything and try and reconnect and rebind the event listeners
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


/////////////////////////
// Quering and Filtering
/////////////////////////

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

var ModelFactory = function(type, opt_schema) {
  var ignored_prefixes = ['_', '$'];

  /**
  * Query is an iterable collection of a Model
  */
  var Query = function() {
    this._filter = [];
    this._order = [];
    this.projection = [];
    this._page_size = 100;
    this._more = false;
    this._dirty = false;
  };

  Query.prototype = new Array();

  /**
  * onChange callback function
  */
  Query.prototype.onchange = undefined;

  Query.prototype.next = function() {
    return true;
  };

  Query.prototype.previous = function() {
    return true;
  };

  Query.prototype.__defineGetter__('more', function() { return this._more; });

  Query.prototype.__defineGetter__('page_size',
      function() { return this._page_size; });
  Query.prototype.__defineSetter__('page_size',
      function(page_size) {
        this._page_size = page_size;
        this._dirty = true;
      });

  Query.prototype.filter = function() {
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
    if (this._filter.length == 0) {
      this._filter = ['AND'];
    }
    this._filter.push(filter);
    return this;
  };

  Query.prototype.order = function(name) {
    this._order.push(ORDER(name));
    return this;
  };

  Query.prototype.serialize = function() {
    return JSON.stringify({
      filter: this._filter,
      order: this._order,
      projection: this.projection,
      page_size: this._page_size
    });
  };

  Query.prototype.fetch = function(opt_callback) {
    var _this = this;
    function callback(data) {
      _this.length = 0;
      _this.push.apply(_this, data);
      var fn = opt_callback || _this.onchange;
      if (fn) {
        fn(_this);
      }
    }
    http.GET('/api/' + type + '/?params=' + this.serialize(), callback);
  };

  function update(model, data) {
    for (var k in data) {
      model[k] = data[k];
    }
  }

  var Model = function() {
  };

  /*
   * Get a model by its id.
   */
  Model.get = function(id, opt_callback) {
    var m = new Model();
    m.Id = id;
    m.$update(opt_callback);
    return m;
  };

  /*
   * query generates a iterator for a query object.
   */
  Model.query = function(opt_callback) {
    var query = new Query();
    // xhr query for collection with timeout to allow for chaining
    setTimeout(function() {
      query.fetch(opt_callback);
    }, 0);
    tailbone.bind(type, function() { query.fetch() });
    return query;
  };

  Model.serialize = function(model) {
    var obj = {};
    for (var member in model) {
      if (ignored_prefixes.indexOf(member[0]) < 0) {
        obj[member] = model[member];
      }
    }
    return obj;
  };

  /*
  * Dollar sign prefix names are ignored on the model as are underscore
  * _name
  * and
  * $name
  * are not included in the jsonifying of an object
  */
  Model.prototype.$save = function(opt_callback) {
    var _this = this;
    http.POST('/api/' + type + '/', Model.serialize(this), function(data) {
      update(_this, data);
      var fn = opt_callback || _this.onchange;
      if (fn) {
        fn(_this);
      }
      tailbone.trigger(type);
    });
  };

  Model.prototype.$delete = function(opt_callback) {
    var _this = this;
    http.DELETE('/api/' + type + '/' + this.Id, function() {
      var fn = opt_callback || _this.onchange;
      if (fn) {
        fn();
      }
      tailbone.trigger(type);
    });
  };

  Model.prototype.$update = function(opt_callback) {
    var _this = this;
    http.GET('/api/' + type + '/' + this.Id, function(data) {
      update(_this, data);
      var fn = opt_callback || _this.onchange;
      if (fn) {
        fn(_this);
      }
    });
  };

  return Model;
};

var User = new ModelFactory('users');

User.login = function(opt_callback) {
  // window.open("/api/login?url=/api/login.html", "popup", "location=1,status=1,scrollbars=1, width=100,height=100");
};

User.logout = function(opt_callback) {
  http.GET('/api/logout', opt_callback);
};

//
// User.get('me', function(me) {
//  if(!me) {
//    User.login(function(me) {
//      doSomething(me);
//    });
//  } else {
//    doSomething(me);
//  }
// });

// Add the channel js for appengine and bind the events.

// Exports
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
  http: http
};

})(this, this.document);
