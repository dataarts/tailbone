/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/2/13
 * Time: 11:04 PM
 */

/**
 * StateDrive
 * @constructor
 */
var StateDrive = function () {

  EventDispatcher.call(this);

  this._state = 0;
  this._callQueue = {};

};

/**
 * Extend EventDispatcher
 * @type {EventDispatcher}
 */
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
 * @param state {int} new state
 */
StateDrive.prototype.setState = function (state) {

  this._state = state;
  this._executeQueuedCalls();

};

/**
 * Specifies minimum state for the member function to execute.
 * A function call of name 'funcName' will be delayed until the instance reaches given 'state'.
 * @param funcName {string} name of member function to set minimum call state for
 * @param validators... {RegExp...} optional validators per argument passed to future function call
 * @param state {int} minimum state value for the member function to execute
 */
StateDrive.prototype.setMinCallState = function (funcName, validators, state) {

  var originalFunction = this[funcName],
    stateId = arguments[arguments.length - 1],
    argumentValidators = arguments.length > 2 ? Array.prototype.slice.apply(arguments).slice(1, arguments.length - 1) : [],
    i;

  this[funcName] = function () {
    if (this._state >= stateId || arguments.length < argumentValidators.length) {
      return originalFunction.apply(this, arguments);
    } else {
      for (i = 0; i < argumentValidators.length; ++i) {
        if (!arguments[i].match(argumentValidators[i])) {
          return originalFunction.apply(this, arguments);
        }
      }
      return this._queueCall(funcName, arguments, stateId);
    }
  };

};

/**
 * Queues function call until a given minimum state is reached.
 * @param funcName {string} name of member function to queue
 * @param args {array} arguments to pass
 * @param state {int} minimum state
 */
StateDrive.prototype._queueCall = function (funcName, args, state) {

  this._callQueue[state] = this._callQueue[state] || [];
  this._callQueue[state].push({name: funcName, args: args});

};

/**
 * Executes queued calls for current and lower states
 */
StateDrive.prototype._executeQueuedCalls = function () {

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
