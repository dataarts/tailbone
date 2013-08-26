/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/2/13
 * Time: 11:28 PM
 */

/**
 * Internal Node utility functions
 * @type {{PROTECTED_EVENTS: Array, uidSeed: number, remoteBindsByNodeIds: {}, upgradeLocal: Function, upgradeRemote: Function, upgradeMutual: Function, send: Function, acknowledgeRemoteBind: Function, acknowledgeRemoteUnbind: Function, doesRemoteBindTo: Function}}
 */
var NodeUtils = {

  PROTECTED_EVENTS: ['open', 'close', 'error', 'connect', 'enter', 'leave', 'bind', 'unbind'],

  uidSeed: 1,
  remoteBindsByNodeIds: {},

  send: function (node, message) {

    var sendChannel = node._channels.filter(function(c) {
      return c.getState() === Channel.STATE.OPEN;
    })[0];

    if (sendChannel) {
      sendChannel.send(message);
    } else {
      console.warn('There is no open send channel.');
    }

  },

  acknowledgeRemoteBind: function (nodeId, type) {

    NodeUtils.remoteBindsByNodeIds[nodeId] = NodeUtils.remoteBindsByNodeIds[nodeId] || [];
    if (NodeUtils.remoteBindsByNodeIds[nodeId].indexOf(type) === -1) {
      NodeUtils.remoteBindsByNodeIds[nodeId].push(type);
    }

  },

  acknowledgeRemoteUnbind: function (nodeId, type) {

    var index;
    if (NodeUtils.remoteBindsByNodeIds[nodeId] && (index = NodeUtils.remoteBindsByNodeIds[nodeId].indexOf(type))) {
      NodeUtils.remoteBindsByNodeIds[nodeId].splice(index, 1);
    }

  },

  doesRemoteBindTo: function (nodeId, type) {

    // if nothing has been external bound assume all things are
    var types = NodeUtils.remoteBindsByNodeIds[nodeId];
    if (types === undefined) {
      return true;
    }

    return types && NodeUtils.remoteBindsByNodeIds[nodeId].indexOf(type) !== -1;

  }

};

// Proxy send function so it can be overridden with out a performance hit
NodeUtils.sendWrapper = NodeUtils.send;

/**
 * Node
 * @param mesh {Mesh} Mesh to which the node belongs
 * @param id {string} Node ID
 * @constructor
 */
var Node = function (mesh, id, initiator) {

  StateDrive.call(this);

  var uid = NodeUtils.uidSeed++;
  this.__defineGetter__('uid', function () {
    return uid;
  });
  this.mesh = mesh;
  this.id = id;
  this._channels = [];
  this._signalingChannel = null;
  this._remotelyBoundTypes = {};

  this.__defineGetter__('initiator', function () {

    return initiator;

  });

  this.setState(Node.STATE.DISCONNECTED);
  this.setMinCallState("connect", Node.STATE.DISCONNECTED);
  this.setMinCallState("disconnect", Node.STATE.CONNECTED);
  this.setMinCallState("bind", Node.STATE.CONNECTED);
  this.setMinCallState("unbind", Node.STATE.CONNECTED);
  this.setMinCallState("_bind", Node.STATE.CONNECTED);
  this.setMinCallState("_unbind", Node.STATE.CONNECTED);
  this.setMinCallState("trigger", Node.STATE.CONNECTED);

};

/**
 * Extend StateDrive
 * @type {StateDrive}
 */
Node.prototype = new StateDrive();

/**
 * Returns unique Node string representation.
 * Essential to make dictionary indexing by Node work.
 * @returns {string}
 */
Node.prototype.toString = function () {

  return 'Node@' + this.uid;

};

/**
 * Connects to remote node
 */
Node.prototype.connect = function (callback) {

  var self = this;
  var state = this.getState();
  if (state === Node.STATE.CONNECTING || state === Node.STATE.CONNECTED) {
    return;
  }

  self.setState(Node.STATE.CONNECTING);

  if (this.mesh.options.ws) {
    this._signalingChannel = new SocketChannel(this.mesh.self, this);
  } else {
    this._signalingChannel = new ChannelChannel(this.mesh.self, this);
  }

  if (self !== self.mesh.self && self.mesh.options.useWebRTC) {
    this._channels.push(new RTCChannel(this.mesh.self, this));
  }
  this._channels.push(this._signalingChannel);

  var propagateMessage = function(e) {
    var args = self.preprocessIncoming(e.data);
    // propagate up
    EventDispatcher.prototype.trigger.apply(self, args);
    if (self !== self.mesh.self) {
      EventDispatcher.prototype.trigger.apply(self.mesh.peers, args);
    }
    EventDispatcher.prototype.trigger.apply(self.mesh, args);
  };

  this._channels.forEach(function (channel) {
    ['open', 'message', 'error', 'close'].forEach(function(type) {
      channel.bind(type, propagateMessage);
    });
  });

  this._signalingChannel.bind('open', function(e) {
    //Broadcast to all newly bound nodes all of your current listeners
    if (self != self.mesh.self) {
      var types = Object.keys(self.mesh._handlers);
      var peers = Object.keys(self.mesh.peers._handlers);
      peers.forEach(function(type) {
        if (types.indexOf(type) === -1) {
          types.push(type);
        }
      });
      types.forEach(function(type) {
        self._bind(type);
      });
      // open all other channels upgrading to webrtc where possible
      self._channels.forEach(function(channel) {
        channel.open();
      });
    }
    self.setState(Node.STATE.CONNECTED);
  });

  this._signalingChannel.open();

};

/**
 * Disconnects node
 */
Node.prototype.disconnect = function () {

  this._channels.forEach(function (channel) {

    channel.unbind('message');
    channel.close();

  });

};

/**
 * Binds an event on the remote node
 * @param type {string}
 * @param handler {function}
 */
Node.prototype.bind = function (type, handler) {
  EventDispatcher.prototype.bind.apply(this, arguments);
  this._bind.apply(this, arguments);
};

Node.prototype._bind = function(type, handler) {
  if (this !== this.mesh.self) {
    if (NodeUtils.PROTECTED_EVENTS.indexOf(type) === -1) {
      var bound = this._remotelyBoundTypes[type];
      if (!bound) {
        this._remotelyBoundTypes[type] = 0;
        NodeUtils.sendWrapper(this, '["bind","' + type + '"]');
      }
      this._remotelyBoundTypes[type] += 1;
    }
  }
};

/**
 * Unbinds event from the remote node
 * @param type {string}
 * @param handler {function}
 */
Node.prototype.unbind = function (type, handler) {
  EventDispatcher.prototype.unbind.apply(this, arguments);
  this._unbind.apply(this, arguments);
};

Node.prototype._unbind = function(type, handler) {
  if (this !== this.mesh.self) {
    if (NodeUtils.PROTECTED_EVENTS.indexOf(type) === -1) {
      this._remotelyBoundTypes[type] -= 1;
      var bound = this._remotelyBoundTypes[type];
      if (bound === 0) {
        NodeUtils.sendWrapper(this, '["unbind","' + type + '"]');
      }
    }
  }
};

/**
 * Triggers remotely on the node
 * @param type
 * @param args
 */
Node.prototype.trigger = function (type, args) {

  // Trigger on self
  if (this === this.mesh.self) {
    EventDispatcher.prototype.trigger.apply(this, arguments);
    // propagate up
    EventDispatcher.prototype.trigger.apply(this.mesh, arguments);
    return;
  }

  if (!NodeUtils.doesRemoteBindTo(this.id, type)) {
    return;
  }

  this._trigger.apply(this, arguments);

};

/**
 * Sends to remote regardless of if it asked for it.
 * Useful for upgrading rtc connections before things are bound fully.
 */
Node.prototype._trigger = function (type, args) {

  var message;

  try {
    var outgoing = this.preprocessOutgoing.apply(this, arguments);
    message = JSON.stringify(Array.prototype.slice.apply(outgoing));
    if (message === 'null') {
      return;
    }

  } catch (e) {

    throw new Error('Trigger not serializable');

  }

  NodeUtils.sendWrapper(this, message);

};

/**
 * Pre-processes incoming event before passing it on to the event pipeline
 * @param eventArguments {array} data
 */
Node.prototype.preprocessIncoming = function (eventArguments) {

  var type = eventArguments[0],
    parsedArguments = [],
    node,
    i;

  switch (type) {

    case 'connect':
      parsedArguments.push(type);
      for (i = 1; i < eventArguments.length; ++i) {
        node = new Node(this.mesh, eventArguments[i], true);
        parsedArguments.push(node);
        // add node
        this.mesh.peers.push(node);
        if (this.mesh.options.autoPeerConnect) {
          node.connect();
        }
      }
      if (this != this.mesh.self) {
        console.warn('Expected "connect" triggered only on self node.')
      }
      // mark mesh and peers as connected
      this.mesh.peers.setState(Node.STATE.CONNECTED);
      this.mesh.setState(Node.STATE.CONNECTED);
      break;

    case 'enter':
      parsedArguments.push(type);
      for (i = 1; i < eventArguments.length; ++i) {
        node = new Node(this.mesh, eventArguments[i], false);
        parsedArguments.push(node);
        // add node
        this.mesh.peers.push(node);
        if (this.mesh.options.autoPeerConnect) {
          node.connect();
        }
      }
      break;

    case 'leave':
      parsedArguments.push(type);
      // TODO: these node objects are not equal to those in the peers list
      for (i = 1; i < eventArguments.length; ++i) {
        node = this.mesh.peers.getById(eventArguments[i]);
        if (node) {
          parsedArguments.push(node);
          // remove node
          this.mesh.peers.splice(this.mesh.peers.indexOf(node), 1);
          node.disconnect();
        } else {
          console.warn('Node', eventArguments[i], 'leave event but not in peers.');
        }
      }
      break;

    case 'bind':
      NodeUtils.acknowledgeRemoteBind(this.id, eventArguments[1]);
      parsedArguments = eventArguments;
      break;

    case 'unbind':
      NodeUtils.acknowledgeRemoteUnbind(this.id, eventArguments[1]);
      parsedArguments = eventArguments;
      break;

    default:
      parsedArguments = eventArguments;
      break;

  }

  return parsedArguments;

};

/**
 * Pre-processes outgoing events before sending them
 * @param type {string} event type
 * @param args {object...} event arguments
 * @returns {Arguments} processed message array ready to be sent
 */
Node.prototype.preprocessOutgoing = function (type, args) {

  if (NodeUtils.PROTECTED_EVENTS.indexOf(type) === -1) {
    return arguments;
  } else {
    throw new Error('Event type ' + type + ' protected');
  }

};

Node.STATE = {

  DISCONNECTED: 1,
  CONNECTING: 2,
  CONNECTED: 3

}