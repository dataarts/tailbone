'use strict';

/*
 * Bi-Directional data binding with AppEngine and the channel api
 */

window.tailbone = (function(window, document, undefined) {

// Do checks for minimum requirements
if (!XMLHttpRequest || !JSON) {
  throw Error('Browser does not support the minimum requirements of ' +
        'XMLHttpRequest, JSON' +
        '. Try adding modernizer to polyfill.');
}

function http(method, url, data, success) {
  var r = new XMLHttpRequest();
  r.open(method, url, true);
  r.onreadystatechange = function() {
    if (r.readyState == 4) {
      var resp = JSON.parse(r.responseText);
      if (resp && resp.error) {
        throw new Error(resp.error);
        return;
      }
      if (success) {
        success(resp);
      }
    }
  };
  r.setRequestHeader('Content-Type', 'application/json');
  if (data) {
    switch (toString.call(data)) {
      case '[object Object]':
        data = JSON.stringify(data);
        break;
      // case '[object String]':
      //   break;
      // case '[object FormData]':
      //   break;
    }
  }
  r.send(data);
}

http.GET = function(url, success) { http('GET', url, null, success); };
http.POST = function(url, data, success) { http('POST', url, data, success); };
http.DELETE = function(url, success) { http('DELETE', url, null, success); };

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
  throw new Error('Channel not connectable.');
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
        JSON.stringify({'method': 'token', 'client_id': client_id}),
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
  if (msg && msg.error) {
    throw new Error(msg.error);
  }
}

function trigger(name, payload) {
  http.POST('/api/events/',
      JSON.stringify({'method': 'trigger',
                      'client_id': client_id,
                      'name': name, 'payload': payload}),
      errorHandler);
}

function bind(name, fn) {
  event_map[name] = event_map[name] || [];
  event_map[name].push(fn);
  http.POST('/api/events/',
      JSON.stringify({'method': 'bind',
                      'client_id': client_id, 'name': name}),
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
      JSON.stringify({'method': 'unbind',
                      'client_id': client_id, 'name': name}),
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

function save(type, model) {
}

function del(type, model) {
}


var ModelFactory = function(type, opt_schema) {
  var ignored_prefixes = ['_', '$'];

  /**
  * Query is an iterable collection of a Model
  */
  var Query = function() {
    this.filter = [];
    this.order = [];
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
    switch (arguments.length) {
      case 1:
        this.filter = this.filter.concat(arguments[0]);
        break;
      case 3:
        this.filter = this.filter.concat(FILTER.call(arguments));
        break;
      default:
        throw Error('Undefined FILTER format.');
    }
  };

  Query.prototype.order = function(name) {
    this.order.push(ORDER(name));
  };

  Query.prototype.serialize = function() {
    return JSON.stringify({
      filter: this.filter,
      order: this.order,
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
    function callback(data) {
      update(m, data);
      var fn = opt_callback || m.onchange;
      if (fn) {
        fn(m);
      }
    }
    http.GET('/api/' + type + '/' + id, callback);
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
    save(type, this);
    var _this = this;
    http.POST('/api/' + type + '/', Model.serialize(this), function() {
      if (opt_callback) {
        opt_callback.call(_this, arguments);
      }
      tailbone.trigger(type);
    });
  };

  Model.prototype.$delete = function(opt_callback) {
    del(type, this);
    tailbone.trigger(type);
  };

  return Model;
};


// Add the channel js for appengine and bind the events.

// Exports
return {
  Model: ModelFactory,
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
