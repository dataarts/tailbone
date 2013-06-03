/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/3/13
 * Time: 1:34 AM
 */

var EventDispatcher = function () {

    this._handlers = {};

};

EventDispatcher.prototype = {

    /**
     * Binds event by name
     * @param type {string} type of event to bind
     * @param handler {function}
     */
    bind: function (type, handler) {

        console.log('* bind', type);
        this._handlers[type] = this._handlers[type] || [];
        this._handlers[type].push(handler);

    },

    /**
     * Unbinds event by name
     * @param type {string} type of event to unbind
     * @param handler {function} (optional)
     */
    unbind: function (type, handler) {

        console.log('* unbind', type);
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
     * @param type {string} type of event to be triggered
     * @param args... {object...} arguments to be passed to event handler
     */
    trigger: function (type, args) {

        var i;

        args = Array.prototype.slice.apply(arguments).slice(1);
        console.log('* trigger', type, args);

        if (this._handlers[type]) {

            for (i = 0; i < this._handlers[type].length; ++i) {

                this._handlers[type][i].apply(this, args);

            }

        }


    }

};
