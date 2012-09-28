'use strict';
/*
 * Bi-Directional data binding with AppEngine and the channel api
 */

window.tailbone = (function(window, document, undefined) {

function POST(url, data, callback) {
  if (XMLHttpRequest) {
    r = new XMLHttpRequest();
    r.onreadystatechange = function() {
      if (r.readyState == 4) {
        callback(JSON.parse(r.responseText));
      }
    };
    r.open('POST', url, true);
    r.setRequestHeader('Content-Type', 'application/json');
    r.send(data);
  } else {
    throw Error('Browser does not support XMLHttpRequest. ' +
        'Try adding modernizer to polyfill.');
  }
}

function GET(url, callback) {
  if (XMLHttpRequest) {
    r = new XMLHttpRequest();
    r.onreadystatechange = function() {
      if (r.readyState == 4) {
        callback(JSON.parse(r.responseText));
      }
    };

    r.open('GET', url, true);
    r.setRequestHeader('Content-Type', 'application/json');
    r.send();
  } else {
    throw Error('Browser does not support XMLHttpRequest. ' +
        'Try adding modernizer to polyfill.');
  }
}

function DELETE(url, callback) {
  if (XMLHttpRequest) {
    r = new XMLHttpRequest();
    r.onreadystatechange = function() {
      if (r.readyState == 4) {
        callback(JSON.parse(r.responseText));
      }
    };
    r.open('DELETE', url, true);
    r.setRequestHeader('Content-Type', 'application/json');
    r.send();
  } else {
    throw Error('Browser does not support XMLHttpRequest. ' +
        'Try adding modernizer to polyfill.');
  }
}


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
    if_connected(bind, event_bindings[i][0], event_bindings[i][1]);
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
      fns[i].call(this, data.payload);
    }
  }
}

function connect(callback) {
  if (callback) queue.push(callback);
  if (!CONNECTING) {
    post('/api/events/',
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

function if_connected(fn, arg1, arg2) {
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
  POST('/api/events/',
      JSON.stringify({'method': 'trigger',
                      'client_id': client_id,
                      'name': name, 'payload': payload}),
      errorHandler);
}

function bind(name, fn) {
  event_map[name] = event_map[name] || [];
  event_map[name].push(fn);
  POST('/api/events/',
      JSON.stringify({'method': 'bind',
                      'client_id': client_id, 'name': name}),
      errorHandler);
}

function unbind(name, fn) {
  if (name) {
    if (fn) {
      var index = event_map[name].indexOf[fn];
      delete event_map[name][index];
    } else {
      delete event_map[name];
    }
  } else {
    event_map = {};
  }
  POST('/api/events/',
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
  ignored_prefixes = ['_', '$'];

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

  Query.prototype.to_json = function() {
    return {
      filter: this.filter,
      order: this.order,
      page_size: this._page_size
    };
  };

  Query.prototype.fetch = function(opt_callback) {
    var _this = this;
    function callback(data) {
      var fn = opt_callback || _this.onchange;
      if (fn) {
        fn(_this);
      }
    }
    GET('/api/' + type + '?params=' + JSON.stringify(this.to_json()), callback);
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
    GET('/api/' + type + '/' + id, callback);
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
    tailbone.bind(type, query.fetch);
    return query;
  };

  Model.to_json = function(model) {
    var obj = {};
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
    tailbone.trigger(type);
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
  trigger: function(name, payload) { if_connected(trigger, name, payload); },
  bind: function(name, fn) { if_connected(bind, name, fn); },
  unbind: function(name, fn) { if_connected(unbind, name, fn); }
};

})(this, this.document);
