/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * @copyright 2013 Google & UNIT9
 * Date: 6/2/13
 * Time: 10:53 PM
 */

var Mesh = function (id, options) {

    /* constructor */
    StateDrivenObject.call(this);
    this.id = id;
    this.config(options);
    this.setState(Mesh.STATE.INITIALISED);
    this.setMinCallState('connect', Mesh.STATE.INITIALISED);
    this.setMinCallState('broadcast', Mesh.STATE.CONNECTED);

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

        console.log('- socket open', self);
        self.setState(Mesh.STATE.CONNECTED);

    };

    var onSocketMessage = function (self, message) {

        console.log('- socket message', message);
        if (!handleSystemMessage(self, message)) {

            handleCustomMessage(self, message);

        }

    };

    var onSocketError = function (self) {

        console.log('- socket error');
        self.setState(Mesh.STATE.UNDEFINED);

    };

    var onSocketClose = function (self) {

        console.log('- socket close');
        self.setState(Mesh.STATE.INITIALISED);

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

Mesh.prototype = new StateDrivenObject();

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

/**
 * Broadcasts message across all nodes
 */
Mesh.prototype.broadcast = function () {

    console.log('* broadcast', arguments, this);

};
