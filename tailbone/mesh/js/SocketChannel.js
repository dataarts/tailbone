/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/4/13
 * Time: 3:01 AM
 */

/**
 * SocketChannel
 * @param localNode {Node}
 * @param remoteNode {Node}
 * @constructor
 */
var SocketChannel = function (localNode, remoteNode) {
  Channel.call(this, localNode, remoteNode);

  this.setState(Channel.STATE.CLOSED);
  this.setMinCallState('send', Channel.STATE.OPEN);
  this.setMinCallState('close', Channel.STATE.OPEN);

  this.multiplexer = SocketMultiplexer.get(localNode.mesh);
};

/**
 * Extend Channel
 * @type {Channel}
 */
SocketChannel.prototype = new Channel();

/**
 * Opens WebSocket connection
 */
SocketChannel.prototype.open = function () {
  this.multiplexer.register(this);
  this.multiplexer.open();
};

/**
 * Closes WebSocket connection
 */
SocketChannel.prototype.close = function () {
  this.multiplexer.close(this);
};

/**
 * Sends message to remoteNode
 * @param message {string}
 */
SocketChannel.prototype.send = function (message) {
  this.multiplexer.send(this, message);
};

