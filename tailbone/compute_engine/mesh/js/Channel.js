/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/5/13
 * Time: 12:16 AM
 */

/**
 * Channel
 * @param localNode {Node}
 * @param remoteNode {Node}
 * @constructor
 */
var Channel = function (localNode, remoteNode) {

    EventDispatcher.call(this);

    this.localNode = localNode;
    this.remoteNode = remoteNode;

};

/**
 * Extend EventDispatcher
 * @type {EventDispatcher}
 */
Channel.prototype = new EventDispatcher();

/**
 * Opens connection channel between local and remote node
 */
Channel.prototype.open = function () {

};

/**
 * Closes connection channel between local and remote node
 */
Channel.prototype.close = function () {

};

/**
 * Sends message to remoteNode
 * @param message
 * @returns {boolean} success
 */
Channel.prototype.send = function (message) {

    return false;

};
