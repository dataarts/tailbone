var port = parseInt(process.argv[2] || '8889')
  , WebSocketServer = require('ws').Server
  , http = require('http');


var app = http.createServer(function(req, res) {
  res.writeHead(200, {'Content-Type': 'text/plain'});
  res.end(''+_count);
});

var wss = new WebSocketServer({server: app});

var _count = 0;
var _global_id = 0;
function generate_id() {
  return ++_global_id;
}

var room_to_peers = {};
var id_to_peer = {};

wss.on('connection', function(ws) {
  _count++;
  ws.id = generate_id();
  id_to_peer[ws.id] = ws;
  var room = ws.upgradeReq.url.substring(1);
  var peers = room_to_peers[room] || [];
  var connect = peers.map(function(p) { return p.id; });
  connect.unshift('connect');
  try {
    ws.send(JSON.stringify([ws.id, JSON.stringify(connect)]));
  } catch(e) {}
  peers.forEach(function(peer) {
    try {
      peer.send(JSON.stringify([peer.id, JSON.stringify(['enter', ws.id])]));
    } catch(e) {}
  });
  peers.push(ws);
  room_to_peers[room] = peers;
  ws.on('message', function(message) {
    function forward(targets, payload) {
      if (!(targets instanceof Array)) {
        console.error('targets not Array.', targets, payload);
        return;
      }
      targets.forEach(function(target_id) {
        var target = id_to_peer[target_id];
        if (target) {
          try {
            target.send(JSON.stringify([ws.id, payload]))
          } catch (e) {}
        } else {
          console.error('target not found.', target_id);
        }
      });
    }
    var msg;
    try {
      msg = JSON.parse(message);
    } catch (e) {
      console.error(e);
      return;
    }
    if (!(msg instanceof Array && msg.length > 0)) {
      console.error('msg not correctly formated.', msg);
      return;
    }
    var targets = msg[0];
    if (targets[0] instanceof Array) {
      msg.forEach(function(m) {
        if (!(m instanceof Array && m.length > 0)) {
          console.error('m not correctly formated.', m);
          return;
        }
        forward(m[0], m[1]);
      });
    } else {
      forward(targets, msg[1]);
    }
  });
  ws.on('close', function() {
    _count--;
    peers.splice(peers.indexOf(ws), 1);
    delete id_to_peer[ws.id];
    peers.forEach(function(peer) {
      try {
        peer.send(JSON.stringify([peer.id, JSON.stringify(['leave', ws.id])]));
      } catch (e) {}
    })
  });
});


app.listen(port);
