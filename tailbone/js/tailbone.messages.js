'use strict';

window.tailbone = !window.tailbone ? {} : window.tailbone;

(function(window, document, undefined) {

function messages(callback) {
  http.GET('/api/messages', function(resp) {
    var channel = new goog.appengine.Channel(resp.token);
    var socket = channel.open();
    // msg must contain a 'to' field which is the target client_id
    socket.send = function(msg) {
      http.POST('/api/messages', msg);
    };
    socket.client_id = resp.client_id;
    // onopen, onmessage, onclose, onerror
    callback(socket)
  });
}

// Exports
tailbone.messages = messages;

})(window, document);