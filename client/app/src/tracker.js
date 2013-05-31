(function() {

  var root = this;
  var previousTracker = root.Tracker || {};

  var Tracker = root.Tracker = function() {

    this.increment = 0;
    this.identifier = generateIdentifier();

    this.ledger = [];
    this.finished = false;

  };

  _.extend(Tracker.prototype, {

    start: function() {

      if (!this.finished) {
        this.finish();
      }

      this.data = [];
      return this;

    },

    finish: function() {

      this.ledger.push(this.data);
      this.finished = true;
      delete this.data;

      return this;

    },

    add: function(data) {

      if (!this.data) {
        this.start();
      }

      console.log(data);

      this.data.push(data);
      this.finished = false;
      return this;

    },

    /**
     * If nothing passed put into localStorage, otherwise save to a database at
     * the specified params
     */
    store: function(ajaxParams) {

      if (!this.finished) {
        this.finish();
      }

      var id = this.identifier + this.increment;
      var data = JSON.stringify(this.ledger);
      delete this.ledger;

      if (_.isObject(ajaxParams)) {
        // TODO: Figure this portion out still.
        ajaxParams.data = data;
        $.ajax(ajaxParams);
      } else {
        localStorage[id] = data;
      }

      this.ledger = [];
      this.increment++;

      return this;

    }

  });

  function generateIdentifier() {

    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
        return v.toString(16);
    });

  }

})();