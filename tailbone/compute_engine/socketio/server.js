require('socket.io').listen(2468);

var bindings = {};
var connections = 0;

io.sockets.on('connection', function (socket) {
    connections += 1;
    socket.on('bind', function (data) {
        var sockets = bindings[data[0]] || [];
        var i = sockets.indexOf(socket);
        if (i < 0) {
            sockets.push(socket);
            bindings[data[0]] = sockets;
        }
    });
    socket.on('unbind', function (data) {
        var sockets = bindings[data[0]] || [];
        var i = sockets.indexOf(socket);
        if (i >= 0) {
            sockets.splice(i, 1);
        }
    });
    socket.on('trigger', function (data) {
        var sockets = bindings[data[0]] || [];
        sockets.forEach(function(s) {
            s.emit('trigger', data);
        });
    });
    socket.on('disconnect', function() {
        connections -= 1;
        // unbind all
        for(k in bindings) {
            var sockets = bindings[k];
            var i = sockets.indexOf(socket);
            if (i >= 0) {
                sockets.splice(i, 1);
            }
        }
        if (connections == 0) {
            console.info("No connections, shutting down.");
        }
    });
});
~
