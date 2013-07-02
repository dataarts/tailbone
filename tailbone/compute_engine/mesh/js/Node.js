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

    PROTECTED_EVENTS: ['open', 'exist', 'enter', 'leave', 'bind', 'unbind'],

    uidSeed: 1,
    remoteBindsByNodeIds: {},

    upgradeLocal: function (node) {

        console.log('update local');

        switch(node.getState()) {

            case Node.STATE.DISCONNECTED:
                node.setState(Node.STATE.WAITING_LOCAL);
                break;

            case Node.STATE.WAITING_REMOTE:
                NodeUtils.upgradeMutual(node);
                break;

        }

    },

    upgradeRemote: function (node, from) {

        console.log('update remote from', from, node.getState());

        switch(node.getState()) {

            case Node.STATE.DISCONNECTED:
                node.setState(Node.STATE.WAITING_REMOTE);
                break;

            case Node.STATE.WAITING_LOCAL:
                NodeUtils.upgradeMutual(node);
                break;

        }

    },

    upgradeMutual: function (node) {

        console.log('mutual upgrade', node.initiator);
        node._channels.forEach(function (channel) {

            channel.open();

        });

    },

    send: function (node, message) {

        var i;

        for (i = node._channels.length - 1; i > -1; --i) {

            if (node._channels[i].send(message)) {

                break;

            }

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

        return NodeUtils.remoteBindsByNodeIds[nodeId] && NodeUtils.remoteBindsByNodeIds[nodeId].indexOf(type) !== -1;

    }

};

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

    this.__defineGetter__('initiator', function () {

        return initiator;

    });

    this.setState(Node.STATE.DISCONNECTED);

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

    if (this.getState() >= Node.STATE.WAITING_LOCAL) {

        return;

    }

    this._channels.push(new SocketChannel(this.mesh.self, this));
    this._channels.push(new RTCChannel(this.mesh.self, this));
    this._signalingChannel = this._channels[0];

    this._channels.forEach(function (channel) {

        channel.bind('open', function () {

            StateDrive.prototype.trigger.call(self, 'open', channel);

        });

        channel.bind('message', function (message) {

            StateDrive.prototype.trigger.apply(self, self.preprocessIncoming.apply(self, message));

        });

    });

    this._signalingChannel.open();

    // Broadcast to all newly bound nodes all of your current listeners
    if (this.mesh.self !== self) {
        for( var type in this.mesh.self._handlers) {
            self.bind(type);
        }
    }

//    this._signalingChannel.send('["connect"]');

//    if (this.mesh.self !== this) {
//
//        NodeUtils.upgradeLocal(this);
//
//    }

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

    if (this === this.mesh.self) {

        StateDrive.prototype.bind.apply(this, arguments);

    } else {

        if (NodeUtils.PROTECTED_EVENTS.indexOf(type) === -1) {

            NodeUtils.send(this, '["bind","' + type + '"]');

        }
    }


};

/**
 * Unbinds event from the remote node
 * @param type {string}
 * @param handler {function}
 */
Node.prototype.unbind = function (type, handler) {

    if (this === this.mesh.self) {

        StateDrive.prototype.unbind.apply(this, arguments);

    } else {

        if (NodeUtils.PROTECTED_EVENTS.indexOf(type) === -1) {

            NodeUtils.send(this, '["unbind","' + type + '"]');

        }
    }

};

/**
 * Triggers remotely on the node
 * @param type
 * @param args
 */
Node.prototype.trigger = function (type, args) {

    var message;

    // Trigger on self
    if (this === this.mesh.self) {
        StateDrive.prototype.trigger.apply(this, arguments);
        return;
    }

    if (!NodeUtils.doesRemoteBindTo(this.id, type)) {

        return;

    }

    try {

        message = JSON.stringify(Array.prototype.slice.apply(this.preprocessOutgoing.apply(this, arguments)));
        if (message === 'null') {
            return;
        }

    } catch (e) {

        throw new Error('Trigger not serializable');

    }

    NodeUtils.send(this, message);

};

/**
 * Pre-processes incoming event before passing it on to the event pipeline
 * @param from {string} from ID
 * @param timestamp {int} timestamp
 * @returns data {array} data
 */
Node.prototype.preprocessIncoming = function (from, timestamp, data) {

    var eventArguments = Array.prototype.slice.apply(arguments).slice(2)[0],
        type = eventArguments[0],
        parsedArguments = [],
        i;


    // we don't want the remote mesh to receive messages from any unrelated node if the channel is common
    if (this._signalingChannel.localNode !== this._signalingChannel.remoteNode && from !== this._signalingChannel.remoteNode.id) {

        return null;

    }
    // console.log(this.id, 'got', data, 'from', from);

    switch (type) {

//        case 'connect':
//            NodeUtils.upgradeRemote(this, from);
//            break;

        case 'exist':
            parsedArguments.push(type);
            for (i = 1; i < eventArguments.length; ++i) {
                var node = new Node(this.mesh, eventArguments[i], true);
                parsedArguments.push(node);
            }
            break;

        case 'enter':
            parsedArguments.push(type);
            for (i = 1; i < eventArguments.length; ++i) {
                var node = new Node(this.mesh, eventArguments[i], false);
                parsedArguments.push(node);
            }
            break;

        case 'leave':
            parsedArguments.push(type);
            // TODO: these node objects are not equal to those in the peers list
            for (i = 1; i < eventArguments.length; ++i) {
                parsedArguments.push(new Node(this.mesh, eventArguments[i], false));
            }
            break;

        case 'bind':
            NodeUtils.acknowledgeRemoteBind(from, eventArguments[1]);
            parsedArguments = eventArguments;
            break;

        case 'unbind':
            NodeUtils.acknowledgeRemoteUnbind(from, eventArguments[1]);
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
    WAITING_REMOTE: 2,
    WAITING_LOCAL: 3,
    CONNECTED: 4

}