'use strict';

window.tailbone = !window.tailbone ? {} : window.tailbone;

(function(window, document, undefined) {

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
// var client_id = Math.random().toString(36).substr(2,25);

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
  name = name.toString();
  event_map[name] = event_map[name] || [];
  http.POST('/api/events/',
      {'method': 'trigger',
       'client_id': client_id,
       'name': name, 'payload': payload},
       null,
       errorHandler);
}

function bind(name, fn) {
  name = name.toString();
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
  	name = name.toString();
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
tailbone._client_id = client_id;
tailbone.databinding = true;
tailbone.trigger = function(name, payload) { ifConnected(trigger, name, payload); };
tailbone.bind = function(name, fn) { ifConnected(bind, name, fn); };
tailbone.unbind = function(name, fn) { ifConnected(unbind, name, fn); };

})(window, document);