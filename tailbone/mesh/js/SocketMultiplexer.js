/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/4/13
 * Time: 3:01 AM
 */

/**
 * Makes the attached channels behave like direct connections.
 */
var SocketMultiplexer = function(mesh) {
  StateDrive.call(this);
  this.mesh = mesh;
  this.setState(Channel.STATE.CLOSED);
  this.setMinCallState('send', Channel.STATE.OPEN);
  this.channels = {};
};

SocketMultiplexer._byMesh = {};

SocketMultiplexer.get = function(mesh) {
  var multiplexer = SocketMultiplexer._byMesh[mesh];
  if(!multiplexer) {
    multiplexer = new SocketMultiplexer(mesh);
    SocketMultiplexer._byMesh[mesh] = multiplexer;
  }
  return multiplexer;
};

SocketMultiplexer.prototype = new StateDrive();

SocketMultiplexer.prototype.register = function(channel) {
  if (this.channels[channel.remoteNode.id] === undefined) {
    this.channels[channel.remoteNode.id] = channel;
    var state = this.getState();
    channel.setState(state);
    // if underlying websocket is already open simulate the open for the channel
    if (state === Channel.STATE.OPEN) {
      channel.trigger('open', {
        timestamp: Date.now(),
        data: ['open']
      });
    }
  }
};

SocketMultiplexer.prototype.unregister = function(channel) {
  delete this.channels[channel.remoteNode.id];
  channel.setState(Channel.STATE.CLOSED);
};

SocketMultiplexer.prototype.open = function(channel) {

  if (this.getState() !== Channel.STATE.CLOSED) {
    return;
  }
  this.setState(Channel.STATE.OPENING);

  var self = this;
  var socket = self.socket = new WebSocket(this.mesh.options.ws);

  socket.addEventListener('open', function(e) {
    self.setState(Channel.STATE.OPEN);
    // mark all attached channels as open
    for (var id in self.channels) {
      var channel = self.channels[id];
      channel.setState(Channel.STATE.OPEN);
      channel.trigger('open', {
        timestamp: Date.now(),
        data: ['open']
      });
    }
  }, false);

  socket.addEventListener('message', function(e) {
    var container;
    try {
      container = JSON.parse(e.data);
    } catch (err) {
      throw new Error('Invalid container received', container);
    }
    var from = container[0];
    var timestamp = container[1];
    var data;
    try {
      data = JSON.parse(container[2]);
    } catch (err) {
      throw new Error('Invalid data received', data);
    }
    // one time upgrade of self id upon connection
    if (data[0] === 'connect') {
      // find a null self node and upgrade it
      var selfChannel = self.channels[null];
      selfChannel.localNode.id = from;
      delete self.channels[null];
      self.channels[from] = selfChannel;
    }
    var fromChannel = self.channels[from];
    if (fromChannel) {
      // console.log('from', fromChannel.remoteNode.id,
      //   'to', fromChannel.localNode.id, data);
      fromChannel.trigger('message', {
        from: fromChannel.remoteNode.id,
        timestamp: timestamp,
        data: data
      });
    } else {
      // console.warn('no from channel found', from);
    }
  }, false);

  socket.addEventListener('close', function() {
    self.setState(Channel.STATE.CLOSED);
    for (var id in self.channels) {
      var channel = self.channels[id];
      channel.setState(Channel.STATE.CLOSED);
      channel.trigger('close', {
        from: channel.remoteNode.id,
        timestamp: Date.now(),
        data: ['close']
      });
    }

  }, false);

  socket.addEventListener('error', function() {
    self.setState(Channel.STATE.CLOSED);
    for (var id in self.channels) {
      var channel = self.channels[id];
      channel.setState(Channel.STATE.CLOSED);
      channel.trigger('error', {
        from: channel.remoteNode.id,
        timestamp: Date.now(),
        data: ['error']
      });
    }
  }, false);

};

SocketMultiplexer.prototype.close = function(channel) {
  this.unregister(channel);
  if (channel.remoteNode === channel.localNode.mesh.self) {
    this.setState(Channel.STATE.CLOSED);
    this.socket.close();
  }
  // if (Object.keys(this.channels).length === 0) {
  //     this.setState(Channel.STATE.CLOSED);
  //     this.socket.close();
  // }
};

var debounce = function(func, wait, immediate) {
  var result;
  var timeout = null;
  return function() {
    var context = this, args = arguments;
    var later = function() {
      timeout = null;
      if (!immediate) result = func.apply(context, args);
    };
    var callNow = immediate && !timeout;
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
    if (callNow) result = func.apply(context, args);
    return result;
  };
};

SocketMultiplexer._send = debounce(function() {

});

SocketMultiplexer.prototype.send = function(channel, message) {
  // this.send._queuedMessages = this.send._queuedMessages || {};
  // var targets = this.send._queuedMessages[message] || [];
  // targets.push(channel.remoteNode.id);
  // this.send._queuedMessages[message] = targets;

  // var self = this;
  // if (!this.send.sendInterval) {
  //   this.send.sendInterval = setInterval(function() {
  //     var msgs = Object.keys(self.send._queuedMessages);
  //     if (msgs.length === 0) {
  //       return;
  //     }
  //     var packets = [];
  //     msgs.forEach(function(msg) {
  //       var recipients = self.send._queuedMessages[msg];
  //       packets.push([recipients, msg]);
  //       delete self.send._queuedMessages[msg];
  //     });
  //     var encoded = JSON.stringify(packets);
  //     self.socket.send(encoded);
  //   }, 100);
  // }

  // return true;

  // TODO: user defer to batch send messages
  var encoded = JSON.stringify([[channel.remoteNode.id], message]);
  return this.socket.send(encoded);
};

