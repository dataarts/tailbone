// TODO: should forEach and filter and such be moved to more compatible syntax?

var Peers = function() {
  Array.call(this);
  StateDrive.call(this);

  this.setState(Node.STATE.DISCONNECTED);

  this.setMinCallState('bind', Node.STATE.CONNECTED);
  this.setMinCallState('unbind', Node.STATE.CONNECTED);
  this.setMinCallState('trigger', Node.STATE.CONNECTED);
};

Peers.prototype = [];
for (var k in StateDrive.prototype) {
  Peers.prototype[k] = StateDrive.prototype[k];
}

Peers.prototype.bind = function() {
  EventDispatcher.prototype.bind.apply(this, arguments);
  this._bind.apply(this, arguments);
};

Peers.prototype._bind = function() {
  var originalArguments = arguments;
  this.forEach(function (peer) {
    peer._bind.apply(peer, originalArguments);
  });
};

Peers.prototype.unbind = function() {
  EventDispatcher.prototype.unbind.apply(this, arguments);
  this._unbind.apply(this, arguments);
};

Peers.prototype._unbind = function() {
  var originalArguments = arguments;
  this.forEach(function (peer) {
    peer._unbind.apply(peer, originalArguments);
  });
};

Peers.prototype.trigger = function() {
  var originalArguments = arguments;
  this.forEach(function(peer) {
    peer.trigger.apply(peer, originalArguments);
  });
};

Peers.prototype.getById = function(node_id) {
  return this.filter(function(peer) { return peer.id === node_id; })[0];
};

