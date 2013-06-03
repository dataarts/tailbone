/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * @copyright 2013 UNIT9 Ltd.
 * Date: 6/2/13
 * Time: 11:04 PM
 */

/**
 * Constructs new StateDrive
 * @constructor
 */
var StateDrive = function () {

    this._state = 0;
    this._callQueue = {};

};

StateDrive.prototype = new EventDispatcher();

/**
 * Gets current object state
 * @returns {int} current state
 */
StateDrive.prototype.getState = function () {

    return this._state;

};

/**
 * Sets current object state
 * @param value {int} new state
 */
StateDrive.prototype.setState = function (value) {

    this._state = value;
    this.executeQueuedCalls();

};

/**
 * Specifies minimum state for the instance function calls. A function call of name 'name' will be delayed until the instance reaches given 'state'
 * @param name {string}
 * @param args... {array...} optional validator
 * @param state {int}
 */
StateDrive.prototype.setMinCallState = function (name, args, state) {

    var originalFunction = this[name],
        stateId = arguments[arguments.length - 1],
        argumentValidators = arguments.length > 2 ? Array.prototype.slice.apply(arguments).slice(1, arguments.length - 1) : [],
        i;

    this[name] = function () {

        if (this._state >= stateId || arguments.length < argumentValidators.length) {

            return originalFunction.apply(this, arguments);

        } else {

            for (i = 0; i < argumentValidators.length; ++i) {

                if (!arguments[i].match(argumentValidators[i])) {

                    return originalFunction.apply(this, arguments);

                }

            }

            return this.queueCall(name, arguments, stateId);

        }

    };

};

/**
 * Queues function call until a given min. state is reached
 * @param name {string}
 * @param args {array}
 * @param state {int}
 */
StateDrive.prototype.queueCall = function (name, args, state) {

    this._callQueue[state] = this._callQueue[state] || [];
    this._callQueue[state].push({name: name, args: args});

};

/**
 * Executes queued calls for current and lower states
 */
StateDrive.prototype.executeQueuedCalls = function () {

    var i, j;

    for (i = 0; i <= this._state; ++i) {

        if (this._callQueue[i]) {

            for (j = 0; j < this._callQueue[i].length; ++j) {

                this[this._callQueue[i][j].name].apply(this, this._callQueue[i][j].args);

            }

            this._callQueue[i] = [];

        }

    }

};
