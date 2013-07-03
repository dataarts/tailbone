/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/4/13
 * Time: 3:01 AM
 */

/**
 * Makes the attached channels behave like direct connections.
 */
var SocketMultiplexer = function(mesh) {
    this.mesh = mesh;
    this.setState(SocketChannel.STATE.CLOSED)
    this.channels = {};
};

SocketMultiplexer._byMesh = {};

SocketMultiplexer.get = function(mesh) {
    var multiplexer = SocketMultiplexer._byMesh[mesh];
    if(!multiplexer) {
        multiplexer = new SocketMultiplexer(mesh);
        SocketMultiplexer._byMesh[mesh] = multiplexer;
    }
    return multiplexer;
};

SocketMultiplexer.prototype = new StateDrive();

SocketMultiplexer.prototype.process = function(from, timestamp, data) {
    // trigger the data on the from channel
    var from = self.channels[from];
    if (from) {
        from.trigger.apply(from, data);
    }
};

SocketMultiplexer.prototype.register = function(channel) {
    if (this.channels[channel.remoteNode.id] === undefined) {
        this.channels[channel.remoteNode.id] = channel;
        channel.setState(this.getState());
        // if underlying websocket is already open simulate the open for the channel
        if (this.getState() === SocketChannel.STATE.OPEN) {
            channel.trigger('open');
        }
    }
};

SocketMultiplexer.prototype.unregister = function(channel) {
    delete this.channels[channel.remoteNode.id];
    channel.setState(SocketChannel.STATE.CLOSED);
};

SocketMultiplexer.prototype.open = function(channel) {

    if (this.getState() == SocketChannel.STATE.OPEN) {
        return;
    }
    this.setState(SocketChannel.STATE.OPEN);

    var self = this;
    var socket = self.socket = new WebSocket(this.mesh.options.ws);

    socket.addEventListener('open', function(e) {
        // mark all attached channels as open
        for (var id in self.channels) {
            var channel = self.channels[id];
            channel.setState(SocketChannel.STATE.OPEN);
            channel.trigger('message', {
                timestamp: Date.now(),
                data: ['open']
            });
        }
    });

    socket.addEventListener('message', function(e) {
        var container;
        try {
            container = JSON.parse(e.data);
        } catch (e) {
            throw new Error('Invalid container received', container);
        }
        var from = container[0];
        var timestamp = container[1];
        var data;
        try {
            data = JSON.parse(container[2]);
        } catch (e) {
            throw new Error('Invalid data received', data);
        }
        // one time upgrade of self id upon connection
        if (data[0] === 'exist') {
            // find a null self node and upgrade it
            var selfChannel = self.channels[null];
            selfChannel.localNode.id = from;
            delete self.channels[null];
            self.channels[from] = selfChannel;
        }
        var fromChannel = self.channels[from];
        console.log('from', fromChannel.remoteNode.id, 
            'to', fromChannel.localNode.id, data);
        if (fromChannel) {
            fromChannel.trigger('message', {
                timestamp: timestamp,
                data: data
            });
        }
    });

    socket.addEventListener('close', function() {
        self.setState(SocketChannel.STATE.CLOSED);
        for (var id in self.channels) {
            var channel = self.channels[id];
            channel.setState(SocketChannel.STATE.CLOSED);
            channel.trigger('message', {
                timestamp: Date.now(),
                data: ['close']
            });
        }

    });

    socket.addEventListener('error', function() {
        for (var id in self.channels) {
            var channel = self.channels[id];
            channel.setState(SocketChannel.STATE.CLOSED);
            channel.trigger('message', {
                timestamp: Date.now(),
                data: ['error']
            });
        }
    });

};

SocketMultiplexer.prototype.close = function(channel) {
    this.unregister(channel);
    if (Object.keys(this.channels).length === 0) {
        this.setState(SocketChannel.STATE.CLOSED);
        this.socket.close();
    }
};

SocketMultiplexer.prototype.send = function(channel, message) {
    // TODO: user defer to batch send messages
    var encoded = JSON.stringify([[channel.remoteNode.id], message]);
    return this.socket.send(encoded);
}
