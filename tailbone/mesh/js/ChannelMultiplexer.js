// TODO: use single appengine.Channel for all mesh's

var ChannelMultiplexer = function(mesh) {
  StateDrive.call(this);
  this.mesh = mesh;
  this.setState(Channel.STATE.CLOSED);
  this.setMinCallState('send', Channel.STATE.OPEN);
  this.channels = {};
};

ChannelMultiplexer._byMesh = {};

ChannelMultiplexer.get = function(mesh) {
  var multiplexer = ChannelMultiplexer._byMesh[mesh];
  if(!multiplexer) {
    multiplexer = new ChannelMultiplexer(mesh);
    ChannelMultiplexer._byMesh[mesh] = multiplexer;
  }
  return multiplexer;
};

ChannelMultiplexer.prototype = new StateDrive();

ChannelMultiplexer.prototype.register = function(channel) {
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

ChannelMultiplexer.prototype.unregister = function(channel) {
  delete this.channels[channel.remoteNode.id];
  channel.setState(Channel.STATE.CLOSED);
};

ChannelMultiplexer.prototype.open = function(channel) {

  if (this.getState() !== Channel.STATE.CLOSED) {
    return;
  }
  this.setState(Channel.STATE.OPENING);

  var self = this;
  var script = document.createElement('script');
  script.src = '/_ah/channel/jsapi';
  document.body.appendChild(script);
  script.onload = function() {

    http.GET('/api/channel/' + self.mesh.id, function(data) {
      var channel = new goog.appengine.Channel(data.token);
      var socket = self.socket = channel.open()
      socket.onopen = function(e) {
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
      };

      socket.onmessage = function(e) {
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
          if (selfChannel) {
            selfChannel.localNode.id = from;
            delete self.channels[null];
            self.channels[from] = selfChannel;
          } else {
            console.warn('Connection already defined for', from);
          }
          if (self.channels[from] == undefined) {
            console.warn('Channel for', from, 'not defined.')
          }
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
      };

      socket.onclose = function() {
        console.log('my channel was closed !!! :(');
        self.setState(Channel.STATE.CLOSED);
        for (var id in self.channels) {
          var channel = self.channels[id];
          channel.setState(Channel.STATE.CLOSED);
          channel.trigger('close', {
            from: fromChannel.remoteNode.id,
            timestamp: Date.now(),
            data: ['close']
          });
        }
      };

      socket.onerror = function() {
        self.setState(Channel.STATE.CLOSED);
        for (var id in self.channels) {
          var channel = self.channels[id];
          channel.setState(Channel.STATE.CLOSED);
          channel.trigger('error', {
            from: fromChannel.remoteNode.id,
            timestamp: Date.now(),
            data: ['error']
          });
        }
      };
    }, function() {
      console.log("Error opening channel.");
      console.log.apply(console, arguments);
    });

  };


};

ChannelMultiplexer.prototype.close = function(channel) {
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

ChannelMultiplexer.prototype.send = function(channel, message) {
  // TODO: user defer to batch send messages
  var msg = [[channel.remoteNode.id], message];
  http.POST('/api/channel/' + this.mesh.id + '/' + this.mesh.self.id, 
            msg,
            function(){});
  return true;
};

