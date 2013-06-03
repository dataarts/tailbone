/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/2/13
 * Time: 10:53 PM
 */

var Mesh = function (id, options) {

    /* constructor */
    StateDrive.call(this);
    this.id = id;
    this.config(options);
    this.setState(Mesh.STATE.INITIALISED);
    this.setMinCallState('connect', Mesh.STATE.INITIALISED);
    this.setMinCallState('trigger', 'test', Mesh.STATE.CONNECTED);
    this.setMinCallState('unbind', /.*/, Mesh.STATE.CONNECTED);

    /* privilaged members */
    /**
     * Connects the Mesh to server
     */
    this.connect = function () {

        var self = this;

        if (!this.options.apiUrl) {

            throw new Error('API URL not specified');

        }

        console.log('* connect');

        restGet(this.options.apiUrl + '/mesh/' + (this.id || ''), function (response) {

            onConnectionPointInfoSuccess(self, response);

        }, function () {

            onConnectionPointInfoFailure();

        });

    };

    /**
     *
     * @param type {string}
     * @param args...
     */
    this.trigger = function (type, args) {

        StateDrive.prototype.trigger.apply(this, arguments);

        var messageArgs = [type],
            messageString;

        messageArgs = messageArgs.concat(Array.prototype.slice.apply(arguments).slice(1));
        try {
            messageString = JSON.stringify(messageArgs);
        } catch (e) {
            return console.log('invalid format');
        }
        console.log('sending', messageArgs);

        if (socket) {

            socket.send(messageString);

        }

    };

    /* private members */
    var socket = null;
    var nodes = [];

    /**
     * Connects to WebSocket server
     * @param self {Mesh}
     * @param url {string}
     */
    var connectToSocket = function (self, url) {

        socket = new WebSocket(url);

        socket.onopen = function () {

            onSocketOpen(self);

        };

        socket.onmessage = function (message) {

            onSocketMessage(self, message);

        };

        socket.onerror = function () {

            onSocketError(self);

        };

        socket.onclose = function () {

            onSocketClose(self);

        }

    };

    var handleSystemMessage = function (self, message) {

//        enter, leave
//        self.handleCustomMessage(self, overriddenMessage);
        return false;

    };

    var handleCustomMessage = function (self, message) {

//        self.trigger(...);

    };

    /**
     * Triggers asynchronous http GET request
     * @param url {string}
     * @param successHandler {function}
     * @param failureHandler {function}
     */
    var restGet = function (url, successHandler, failureHandler) {

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

    };

    /* handlers */
    var onConnectionPointInfoSuccess = function (self, info) {

        var infoObject;

        try {

            infoObject = JSON.parse(info);

        } catch (e) {

            throw new Error('Could not establish connection with server');

        }

        console.log('- connection point', infoObject);
        connectToSocket(self, infoObject.url);

    };

    var onConnectionPointInfoFailure = function () {

        throw new Error('Could not establish connection with server');

    };

    var onSocketOpen = function (self) {

        self.setState(Mesh.STATE.CONNECTED);
        self.trigger('open');

    };

    var onSocketMessage = function (self, message) {

        console.log('- socket message', message);
        if (!handleSystemMessage(self, message)) {

            handleCustomMessage(self, message);

        }

    };

    var onSocketError = function (self) {

        self.setState(Mesh.STATE.UNDEFINED);
        self.trigger('error');

    };

    var onSocketClose = function (self) {

        self.setState(Mesh.STATE.INITIALISED);
        self.trigger('close');

    };

};

Mesh.STATE = {

    INVALID: -1,
    UNDEFINED: 0,
    INITIALISED: 1,
    CONNECTED: 2

};

/**
 * Default Mesh options
 * @type {{apiUrl: null}}
 */
Mesh.options = {

    apiUrl: null

};

Mesh.prototype = new StateDrive();

/**
 * Extends shared Mesh.options with custom config
 * @param options {object}
 */
Mesh.prototype.config = function (options) {

    var field;

    this.options = {};

    for (field in Mesh.options) {

        this.options[field] = Mesh.options[field];

    }

    if (typeof options === 'object') {

        for (field in options) {

            this.options[field] = options[field];

        }

    }

};
