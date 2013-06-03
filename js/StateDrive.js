/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * @copyright 2013 UNIT9 Ltd.
 * Date: 6/2/13
 * Time: 11:04 PM
 */

/**
 * Constructs new StateDrivenObject
 * @constructor
 */
var StateDrivenObject = function () {

    this._state = 0;
    this._callQueue = {};

};

StateDrivenObject.prototype = new EventDispatcher();

/**
 * Gets current object state
 * @returns {int} current state
 */
StateDrivenObject.prototype.getState = function () {

    return this._state;

};

/**
 * Sets current object state
 * @param value {int} new state
 */
StateDrivenObject.prototype.setState = function (value) {

    this._state = value;
    this.executeQueuedCalls();

};

/**
 * Specifies minimum state for the instance function calls. A function call of name 'name' will be delayed until the instance reaches given 'state'
 * @param name {string}
 * @param state {int}
 */
StateDrivenObject.prototype.setMinCallState = function (name, state) {

    var originalFunction = this[name];

    this[name] = function () {

        if (this._state >= state) {

            originalFunction.apply(this, arguments);

        } else {

            this.queueCall(name, arguments, state);

        }

    };

};

/**
 * Queues function call until a given min. state is reached
 * @param name {string}
 * @param args {array}
 * @param state {int}
 */
StateDrivenObject.prototype.queueCall = function (name, args, state) {

    this._callQueue[state] = this._callQueue[state] || [];
    this._callQueue[state].push({name: name, args: args});

};

/**
 * Executes queued calls for current and lower states
 */
StateDrivenObject.prototype.executeQueuedCalls = function () {

    var i, j;

    for (i = 0; i <= this._state; ++i) {

        if (this._callQueue[i]) {

            for (j = 0; j < this._callQueue[i].length; ++j) {

                this[this._callQueue[i][j].name].apply(this, this._callQueue[i][j].arguments);

            }

            this._callQueue[i] = [];

        }

    }

};
