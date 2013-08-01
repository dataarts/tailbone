/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/3/13
 * Time: 1:34 AM
 */

/**
 * EventDispatcher
 * @constructor
 */
var EventDispatcher = function () {

  this._handlers = {};

};

EventDispatcher.prototype = {

  /**
   * Binds event by type
   * @param type {string} type of event to bind to
   * @param handler {function} handler function
   */
  bind: function (type, handler) {

    this._handlers[type] = this._handlers[type] || [];
    if (this._handlers[type].indexOf(handler) === -1) {
      this._handlers[type].push(handler);
    }

  },

  /**
   * Unbinds event by name
   * @param type {string} (optional) type of event to unbind
   * @param handler {function} (optional) particular handler to unbind
   */
  unbind: function (type, handler) {

    if (this._handlers[type]) {
      if (handler) {
        this._handlers[type].splice(this._handlers[type].indexOf(handler), 1);
      } else {
        this._handlers[type] = [];
      }
    }

  },

  /**
   * Triggers event of given type type passes arguments to handlers
   * @param type {string} type of event to trigger
   * @param args... {object...} arguments to be passed to event handler
   */
  trigger: function (type, args) {

    var i;
    args = Array.prototype.slice.apply(arguments).slice(1);
    if (this._handlers[type]) {
      for (i = 0; i < this._handlers[type].length; ++i) {
        this._handlers[type][i].apply(this, args);
      }
    }

  }

};