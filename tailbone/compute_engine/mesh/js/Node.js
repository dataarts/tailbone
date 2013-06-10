/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/2/13
 * Time: 11:28 PM
 */

/**
 * Internal Node utility functions
 * @type {{send: Function}}
 */
var NodeUtils = {

    uidSeed: 1,

    send: function (node, message) {

        var i;

        for (i = node._channels.length - 1; i > -1; --i) {
;
            if (node._channels[i].send(message)) {

                break;

            }

        }

    }

};

/**
 * Node
 * @param mesh {Mesh} Mesh to which the node belongs
 * @param id {string} Node ID
 * @constructor
 */
var Node = function (mesh, id) {

    StateDrive.call(this);

    var uid = NodeUtils.uidSeed++;
    this.__defineGetter__('uid', function () {
        return uid;
    });
    this.mesh = mesh;
    this.id = id;
    this._channels = [];

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
Node.prototype.connect = function () {

    var self = this;

    if (this._channels.length === 0) {

        this._channels.push(new SocketChannel(this.mesh.self, this));
        this._channels.push(new RTCChannel(this.mesh.self, this));

    }

    this._channels.forEach(function (channel) {

        channel.bind('open', function () {

            StateDrive.prototype.trigger.call(self, 'open', channel);

        });

        channel.bind('message', function (message) {

            StateDrive.prototype.trigger.apply(self, self.preprocessIncoming.apply(self, message));

        });

        channel.open();

    });

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

    StateDrive.prototype.bind.apply(this, arguments);


};

/**
 * Triggers remotely on the node
 * @param type
 * @param args
 */
Node.prototype.trigger = function (type, args) {

    var message;

    try {

        message = JSON.stringify(Array.prototype.slice.apply(this.preprocessOutgoing.apply(this, arguments)));

    } catch (e) {

        throw new Error('Trigger not serializable');

    }

    NodeUtils.send(this, message);

};

/**
 * Pre-processes incoming event before passing it on to the event pipeline
 * @param type {string} event type
 * @param args {object...} event arguments
 * @returns {Arguments} processed message array ready to be passed down the event line
 */
Node.prototype.preprocessIncoming = function (type, args) {

    var parsedArguments = [],
        i;

    switch (type) {

        case 'exist':
        case 'enter':
        case 'leave':
            parsedArguments.push(type);
            for (i = 1; i < arguments.length; ++i) {
                parsedArguments.push(new Node(this.mesh, arguments[i]));
            }
            break;

        default:
            parsedArguments = arguments;
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

    return arguments;

};