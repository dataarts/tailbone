/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/4/13
 * Time: 3:02 AM
 */

/**
 * RTCChannel
 * @param localNode {Node}
 * @param remoteNode {Node}
 * @constructor
 */
var RTCChannel = function (localNode, remoteNode) {

    Channel.call(this, localNode,  remoteNode);

};

/**
 * Extend Channel
 * @type {Channel}
 */
RTCChannel.prototype = new Channel();

/**
 * Sends message to remoteNode
 * @param message {string}
 */
RTCChannel.prototype.send = function (message) {

    return Channel.prototype.send.call(this, message);

};
