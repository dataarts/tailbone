/*
 * Bi-Directional data binding with AppEngine and the channel api
 */

window.tailbone = (function(window, document, undefined) {

function post(url, data, callback) {
  var r = new XMLHttpRequest();
  if (r) {
    r.onreadystatechange = function() {
      if (r.readyState == 4) {
        callback(JSON.parse(r.responseText));
      }
    };
    r.open("POST", url, true);
    r.setRequestHeader("Content-Type","application/json");
    r.send(data);
  } else {
    throw Error("Browser does not support post. Try adding modernizer to polyfill.");
  }
}


var CONNECTED = false;
var CONNECTING = false;
var BACKOFF = 1;

var event_map = {};
var queue = [];
var socket;

co

function onOpen() {
  CONNECTED = true;
  BACKOFF = 1;
  for(i=0,l=queue.length;i<l;i++) {
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
  for (var i=0,l=event_bindings.length; i<l; i++) {
    if_connected(bind, event_bindings[i][0], event_bindings[i][1]);
  }
}

function onClose() {
  CONNECTED = false;
  CONNECTING = false;
  rebind();
}

function onError() {
  // TODO: try reconnecting with backoff or alert system of lack of channel capability
  //    throw new Error("ERROR", arguments)
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
    for(i=0,l=fns.length;i<l;i++) {
      fns[i].call(this, data.payload);
    }
  }
}

function connect(callback) {
  if (callback) queue.push(callback);
  if (!CONNECTING) {
    post("/_bidi", JSON.stringify({"method": "token"}), function(token) {
      var channel = new goog.appengine.Channel(token);
      socket = channel.open();
      socket.onopen = onOpen;
      socket.onmessage = onMessage;
      socket.onclose = onClose;
      socket.onerror = onError;
    });
  } else {
    CONNECTING = true;
  }
}

function if_connected(fn, arg1, arg2) {
  var _this = this;
  if (CONNECTED) {
    fn.call(_this, arg1, arg2);
  } else {
    connect(function(){fn.call(_this, arg1, arg2);});
  }
}

function errorHandler(msg) {
  if (msg) {
    msg = JSON.parse(msg);
    if (msg && msg.error && console && console.log) {
      console.log(msg.error);
    }
  }
}

function trigger(name, payload) {
  post("/gaeplus/events",
      JSON.stringify({"method": "trigger", "name": name, "payload": payload}),
      errorHandler);
}

function bind(name, fn) {
  event_map[name] = event_map[name] || [];
  event_map[name].push(fn);
  post("/gaeplus/events", JSON.stringify({"method": "bind", "name": name}), errorHandler);
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
  post("/gaeplus/events", JSON.stringify({"method": "unbind", "name": name}), errorHandler);
}


Model = function() {
};

Model.query = function() {

};

/*
 * Dollar sign prefix names are ignored on the model as are underscore
 * _name
 * and
 * $name
 * are not included in the jsonifying of an object
 */
Model.prototype.$save = function() {

};

Model.prototype.$delete = function() {

};

// Add the channel js for appengine and bind the events.


// Exports
return {
  Model: Model
}

})(this, this.document);
