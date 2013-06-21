/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/4/13
 * Time: 3:01 AM
 */

/**
 *
 * @type {{socketsByLocalNode: {}, batchSendTimeoutIdsBySocket: {}, sendToIdsBySocket: {}}}
 */
var SocketChannelUtils = {

    socketsByLocalNode: {},
    batchSendTimeoutIdsBySocket: {},
    sendToIdsBySocket: {}

};

/**
 * SocketChannel
 * @param localNode {Node}
 * @param remoteNode {Node}
 * @constructor
 */
var SocketChannel = function (localNode, remoteNode) {

    Channel.call(this, localNode, remoteNode);

    this.setState(SocketChannel.STATE.CLOSED);
    this.setMinCallState('send', SocketChannel.STATE.OPEN);

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

    var self = this,
        socket = SocketChannelUtils.socketsByLocalNode[this.localNode.uid];

    if (socket) {

        self.setState(SocketChannel.STATE.OPEN);

    } else {

        socket = new WebSocket(this.localNode.mesh.options.ws);
        SocketChannelUtils.socketsByLocalNode[this.localNode.uid] = socket;
        SocketChannelUtils.batchSendTimeoutIdsBySocket[socket] = -1;
        SocketChannelUtils.sendToIdsBySocket[socket] = [];

    }

    socket.addEventListener('open', function () {

        self.trigger('open');
        self.setState(SocketChannel.STATE.OPEN);

    });

    socket.addEventListener('message', function (message) {

        var messageObject;

        try {

            messageObject = JSON.parse(message.data);

        } catch (e) {

            throw new Error('Invalid message received', message);

        }

        self.trigger('message', messageObject);

    });

    socket.addEventListener('close', function () {

        self.trigger('close');

    });

    socket.addEventListener('error', function () {

        self.trigger('error');

    });

};

/**
 * Closes WebSocket connection
 */
SocketChannel.prototype.close = function () {

    var socket = SocketChannelUtils.socketsByLocalNode[this.localNode.uid];

    if (socket) {

        // TODO: remove event listeners (make them referencable first)

        if (this.remoteNode === this.localNode) {

            socket.close();
            socket.onopen = socket.onmessage = socket.onclose = socket.onerror = null;
            delete SocketChannelUtils.socketsByLocalNode[this.localNode.uid];

        }

    }

};

/**
 * Sends message to remoteNode
 * @param message {string}
 */
SocketChannel.prototype.send = function (message) {

    var socket = SocketChannelUtils.socketsByLocalNode[this.localNode.uid];

    if (socket) {

        clearTimeout(SocketChannelUtils.batchSendTimeoutIdsBySocket[socket]);
        SocketChannelUtils.sendToIdsBySocket[socket].push(this.remoteNode.id);

        SocketChannelUtils.batchSendTimeoutIdsBySocket[socket] = setTimeout(function () {

            socket.send('[' + JSON.stringify(SocketChannelUtils.sendToIdsBySocket[socket]) + ',' + message + ']');
            SocketChannelUtils.sendToIdsBySocket[socket] = [];

        }, 1);

        return true;

    }

    return false;

};

/**
 * SocketChannel states
 * @type {{CONNECTED: number}}
 */
SocketChannel.STATE = {

    CLOSED: 1,
    OPEN: 2

};