var ChannelChannel = function (localNode, remoteNode) {
  Channel.call(this, localNode, remoteNode);

  this.setState(Channel.STATE.CLOSED);
  this.setMinCallState('send', Channel.STATE.OPEN);
  this.setMinCallState('close', Channel.STATE.OPEN);

  this.multiplexer = ChannelMultiplexer.get(localNode.mesh);
};

/**
 * Extend Channel
 * @type {Channel}
 */
ChannelChannel.prototype = new Channel();

/**
 * Opens WebSocket connection
 */
ChannelChannel.prototype.open = function () {
  this.multiplexer.register(this);
  this.multiplexer.open();
};

/**
 * Closes WebSocket connection
 */
ChannelChannel.prototype.close = function () {
  this.multiplexer.close(this);
};

/**
 * Sends message to remoteNode
 * @param message {string}
 */
ChannelChannel.prototype.send = function (message) {
  this.multiplexer.send(this, message);
};

