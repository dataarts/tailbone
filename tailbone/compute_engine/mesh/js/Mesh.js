/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/2/13
 * Time: 10:53 PM
 */

var MeshUtils = {

    SPECIAL: ['open', 'close', 'enter', 'leave', 'exist'],

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

        console.log('- socket message', message);
        if (!handleSystemMessage(self, message)) {
            handleCustomMessage(self, message);
        }

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

    StateDrive.call(this);

    this.id = id;
    this._socket = null;
    this.nodes = [];
    this.config(options);
    this.setState(Mesh.STATE.INITIALISED);
    this.setMinCallState('connect', Mesh.STATE.INITIALISED);
    this.setMinCallState('trigger', 'test', Mesh.STATE.CONNECTED);
    this.setMinCallState('unbind', /.*/, Mesh.STATE.CONNECTED);

};

Mesh.prototype = new StateDrive();

Mesh.prototype.connect = function () {

    var self = this;

    if (this.options.ip) {  // TODO: change to url once backend returns it

        this.options.wsUrl = 'ws://' + this.options.ip + ':2345/' + this.options.name;  // TODO: remove
        console.log('connecting directly to socket', this.options.wsUrl);
        MeshUtils.connectToSocket(self, this.options.wsUrl);

    } else if (this.options.apiUrl) {

        console.log('requesting connection URL from the API');
        MeshUtils.restGet(this.options.apiUrl + '/' + (this.id || ''), function (response) {
            MeshUtils.onConnectionPointInfoSuccess(self, response);
        }, function () {
            MeshUtils.onConnectionPointInfoFailure();
        });

    }

};

Mesh.prototype.trigger = function (type) {

    var messageArgs = [type],
        messageString,
        i;

    StateDrive.prototype.trigger.apply(this, arguments);

    messageArgs = messageArgs.concat(Array.prototype.slice.apply(arguments).slice(1));
    try {
        messageString = JSON.stringify(messageArgs);
    } catch (e) {
        return console.log('invalid format');
    }
    console.log('sending', messageArgs);

    for (i = 0; i < this.nodes.length; ++i) {

        this.nodes[i].trigger.apply(this.nodes[i], arguments);

    }

}

Mesh.prototype.config = function (options) {

    var field;

    this.options = {};

    for (field in Mesh.options) {
        this.options[field] = Mesh.options[field];
    }

    if (typeof options === 'string') {
        this.options.apiUrl = options;
    } else if (typeof(options) === 'object') {
        for (field in options) {
            this.options[field] = options[field];
        }
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
