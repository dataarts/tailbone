/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/2/13
 * Time: 10:53 PM
 */

var MeshUtils = {

    connectToSocket: function (self, url) {

        self._socket = new WebSocket(url);

        self._socket.onopen = function () {
            MeshUtils.onSocketOpen(self);
        };

        self._socket.onmessage = function (message) {
            MeshUtils.onSocketMessage(self, message);
        };

        self._socket.onerror = function () {
            MeshUtils.onSocketError(self);
        };

        self._socket.onclose = function () {
            MeshUtils.onSocketClose(self);
        }

    },

    restGet: function (url, successHandler, failureHandler) {

        var xmlhttp;

        if (window.XMLHttpRequest) {
            xmlhttp = new XMLHttpRequest();
        } else {
            xmlhttp = new ActiveXObject("Microsoft.XMLHTTP");
        }

        xmlhttp.onreadystatechange = function() {
            if (xmlhttp.readyState === 4) {
                if (xmlhttp.status === 200 && typeof successHandler === 'function') {
                    successHandler(xmlhttp.responseText);
                } else {
                    failureHandler(xmlhttp.status);
                }
            }
        }

        xmlhttp.open('GET', url, true);
        xmlhttp.send();

    },

    parseMessage: function (self, message) {

        console.log('- parsing', message);
        switch (message[0]) {
            case 'exist':
            case 'enter':
                console.log('creating nodes for ', arguments);
                break;
        }

    },

    onConnectionPointInfoSuccess: function (self, info) {

        try {
            var options = JSON.parse(info);
            self.config(options);
            self.connect();
        } catch (e) {
            throw new Error('Could not establish connection with server');
        }

    },

    onConnectionPointInfoFailure: function () {

        throw new Error('Could not establish connection with server');

    },

    onSocketOpen: function (self) {

        self.setState(Mesh.STATE.CONNECTED);
        StateDrive.prototype.trigger.call(self, 'open');

    },

    onSocketMessage: function (self, message) {

        var messageObject;
        try {
            messageObject = JSON.parse(message.data);
        } catch (e) {
            console.warn('invalid message received', message);
        }
        // TODO: check timestamp and ensure messages execute in correct order
        MeshUtils.parseMessage(self, messageObject[2]);
        StateDrive.prototype.trigger.apply(self, messageObject[2]);

    },

    onSocketError: function (self) {

        self.setState(Mesh.STATE.UNDEFINED);
        StateDrive.prototype.trigger.call(self, 'error');

    },

    onSocketClose: function (self) {

        self.setState(Mesh.STATE.INITIALISED);
        StateDrive.prototype.trigger.call(self, 'close');

    }

};

var Mesh = function (id, options) {

    if (!WebSocket) {
        throw new Error('WebSockets not supported');
    }

    StateDrive.call(this);

    this.id = id;
    this._socket = null;
    this.self = null;
    this.peers = [];
    this.config(options);
    this.setState(Mesh.STATE.INITIALISED);
    this.setMinCallState('connect', Mesh.STATE.INITIALISED);
    this.setMinCallState('trigger', 'connect', Mesh.STATE.CONNECTED);
    this.setMinCallState('unbind', /.*/, Mesh.STATE.CONNECTED);

};

Mesh.prototype = new StateDrive();

Mesh.prototype.connect = function () {

    var self = this;

    if (this.options.ws) {

        console.log('connecting directly to socket', this.options.ws);
        MeshUtils.connectToSocket(self, this.options.ws);

    } else if (this.options.api) {

        console.log('requesting connection URL from the API');
        MeshUtils.restGet(this.options.api + '/' + (this.id || ''), function (response) {
            MeshUtils.onConnectionPointInfoSuccess(self, response);
        }, function () {
            MeshUtils.onConnectionPointInfoFailure();
        });

    }

};

Mesh.prototype.config = function (options) {

    var field;

    this.options = {};

    for (field in Mesh.options) {
        this.options[field] = Mesh.options[field];
    }

    if (typeof options === 'string') {
        this.options.api = options;
    } else if (typeof(options) === 'object') {
        for (field in options) {
            this.options[field] = options[field];
        }
    }

};

Mesh.prototype.trigger = function () {

    var i;
    StateDrive.prototype.trigger.apply(this, arguments);
    console.log('sending', arguments);
    for (i = 0; i < this.peers.length; ++i) {
        this.peers[i].trigger.apply(this.peers[i], arguments);
    }

};

Mesh.STATE = {

    INVALID: -1,
    UNDEFINED: 0,
    INITIALISED: 1,
    CONNECTED: 2

};

Mesh.options = {

    apiUrl: null

};
