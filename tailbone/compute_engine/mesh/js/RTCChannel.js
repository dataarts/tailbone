/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/4/13
 * Time: 3:02 AM
 */

var RTCChannelUtils = {

    RTCPeerConnection: window.RTCPeerConnection || window.webkitRTCPeerConnection || window.mozRTCPeerConnection

};

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
 * Opens channel
 */
RTCChannel.prototype.open = function () {

    console.log('trying to open RTCChannel with', RTCChannelUtils.RTCPeerConnection);

};

/**
 * Closes channel
 */
RTCChannel.prototype.close = function () {

};

/**
 * Sends message to remoteNode
 * @param message {string}
 */
RTCChannel.prototype.send = function (message) {

    return Channel.prototype.send.call(this, message);

};
