/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/2/13
 * Time: 10:53 PM
 */

/**
 * Internal Mesh utility functions
 */
var MeshUtils = {

  uidSeed: 1,

};


/**
 * Mesh
 * @param id {string} ID of Mesh to join or create, or undefined to create new Mesh and generate ID
 * @param options {string|object} string URL of load balancer API or actual config object
 * @constructor
 */
var Mesh = function (id, options) {

  var self = this;

  StateDrive.call(this);

  if (id && typeof id !== 'string') {

    throw new Error('Invalid type ID');

  }

  var uid = MeshUtils.uidSeed++;
  this.__defineGetter__('uid', function () {
    return uid;
  });

  this.id = id;
  this.self = new Node(this, null);

  this.peers = new Peers();
  this.options = {};

  this.config(options);
  this.setState(Node.STATE.DISCONNECTED);

  this.setMinCallState('connect', Node.STATE.DISCONNECTED);

  this.setMinCallState('bind', Node.STATE.CONNECTED);
  this.setMinCallState('unbind', Node.STATE.CONNECTED);
  this.setMinCallState('trigger', Node.STATE.CONNECTED);

  if (this.options.autoConnect) {
    self.connect();
  }

};

/**
 * Extend StateDrive
 * @type {StateDrive}
 */
Mesh.prototype = new StateDrive();

/**
 * Returns unique Mesh string representation.
 * Essential to make dictionary indexing by Node work.
 * @returns {string}
 */
Mesh.prototype.toString = function () {

  return 'Mesh@' + this.uid;

};

/**
 * Configures mesh
 * @param options {string|object} string URL of load balancer API or actual config object
 */
Mesh.prototype.config = function (options) {

  var field;

  for (field in Mesh.options) {
    this.options[field] = this.options[field] === undefined ? Mesh.options[field] : this.options[field];
  }

  if (typeof options === 'string') {
    this.options.api = options;
  } else if (typeof options === 'object') {
    for (field in options) {
      this.options[field] = options[field];
    }
  }

  // Debug tool to add artificial delays to the mesh call for testing
  var delay = this.options.delay;
  if (typeof delay  == "number") {
    if (delay > 0) {
      NodeUtils.sendWrapper = function() {
        var ctx = this;
        var args = arguments;
        setTimeout(function() {
          NodeUtils.send.apply(ctx, args);
        }, delay);
      }
    }
  } else if (typeof delay === "function") {
    NodeUtils.sendWrapper = function() {
      var ctx = this;
      var args = arguments;
      setTimeout(function() {
        NodeUtils.send.apply(ctx, args);
      }, delay())
    }
  }

};

/**
 * Connects self Node to the mesh.
 * If WebSocket IP is specified, attempts direct connection.
 * Otherwise, attempts to retrieve config object from load balancer via its API url.
 */
Mesh.prototype.connect = function () {

  var self = this,
    options,
    idMatch;

  if (this.options.ws) {

    idMatch = this.options.ws.match('[^\/]+$');
    if (idMatch) {
      this.id = idMatch[0];
    }

    this.self.connect();
    this.peers.forEach(function (peer) {
      peer.connect();
    });

  } else if (this.options.channel) {

    this.id = this.options.name;

    this.self.connect();
    this.peers.forEach(function (peer) {
      peer.connect();
    });

  } else if (this.options.api) {

    http.GET(this.options.api + '/' + (this.id || ''), function (options) {

      self.config(options);
      self.connect();

    }, function () {

      console.warn("Error connecting to server, retrying in 10 seconds.");
      setTimeout(function() {
        self.connect();
      }, 10*1000);

      // throw new Error('Could not establish connection with server');

    });

  } else {

    throw new Error('Invalid options');

  }

};

/**
 * Disconnects all Nodes
 */
Mesh.prototype.disconnect = function () {

  this.self.disconnect();

  this.peers.forEach(function (peer) {
    peer.disconnect();
  });

};

/**
 * Binds event
 * @param type
 * @param handler
 */
Mesh.prototype.bind = function (type, handler) {

  EventDispatcher.prototype.bind.apply(this, arguments);
  this.peers._bind.apply(this.peers, arguments);

};

/**
 * Unbinds event
 * @param type
 * @param handler
 */
Mesh.prototype.unbind = function (type, handler) {

  EventDispatcher.prototype.unbind.apply(this, arguments);
  this.peers._unbind.apply(this.peers, arguments);

};

/**
 * Triggers event
 * @param type
 * @param args
 */
Mesh.prototype.trigger = function (type, args) {

  this.self.trigger.apply(this.self, arguments);
  this.peers.trigger.apply(this.peers, arguments);

};


/**
 * Common Mesh options
 * @type {{api: '/api/mesh', autoConnect: boolean}}
 */
Mesh.options = {

  api: '/api/mesh',
  autoConnect: true,
  autoPeerConnect: true,
  useWebRTC: true,
  delay: undefined

};
