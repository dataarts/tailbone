var socket = io.connect('http://173.255.117.180:2468');

var bindings = {};

function bind(e, fn) {
  var fns = bindings[e] || [];
  var i = fns.indexOf(fn);
  if (i <= 0) {
    fns.push(fn);
    bindings[e] = fns;
  }
  socket.emit('bind', [e]);
}

function trigger() {
  var args = Array.prototype.slice.call(arguments);
  socket.emit('trigger', args);
}

socket.on('trigger', function(data) {
  var fns = bindings[data[0]] || [];
  fns.forEach(function(fn) {
    fn.apply(this, data.slice(1));
  });
});

function unbind(e, fn) {
  var fns = bindings[e] || [];
  if (fns) {
    if (fn) {
      var i = fns.indexOf(fn);
      if (i <= 0) {
        bindings[e].splice(i, 1);
      }
    } else {
      bindings[e] = [];
    }
  }
  socket.emit('unbind', [e]);
}