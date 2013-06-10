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
        socket = SocketChannelUtils.socketsByLocalNode[this.localNode];

    if (socket) {

        // do nothing

    } else {

        socket = new WebSocket(this.localNode.mesh.options.ws);
        SocketChannelUtils.socketsByLocalNode[this.localNode] = socket;
        SocketChannelUtils.batchSendTimeoutIdsBySocket[socket] = -1;
        SocketChannelUtils.sendToIdsBySocket[socket] = [];

        socket.addEventListener('open', function () {

            self.trigger('open');

        });

        socket.addEventListener('message', function (message) {

            var messageObject;

            try {

                messageObject = JSON.parse(message.data)[2];

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

    }

    // we don't want to listen on remote nodes as the messages arrive to local node anyway (shared socket)

};

/**
 * Closes WebSocket connection
 */
SocketChannel.prototype.close = function () {

    var socket = SocketChannelUtils.socketsByLocalNode[this.localNode];

    if (socket) {

        // TODO: remove event listeners (make them referencable first)

        if (this.remoteNode === this.localNode) {

            socket.close();
            socket.onopen = socket.onmessage = socket.onclose = socket.onerror = null;
            delete SocketChannelUtils.socketsByLocalNode[this.localNode];

        }

    }

};

/**
 * Sends message to remoteNode
 * @param message {string}
 */
SocketChannel.prototype.send = function (message) {

    var socket = SocketChannelUtils.socketsByLocalNode[this.localNode];

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
