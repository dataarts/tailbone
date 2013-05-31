(function() {

  var root = this;
  var previousTimeline = root.Timeline || {};

  var Timeline = root.Timeline = function(options) {

    var params = _.defaults(options || {}, {
      start: 0,
      end: 5000,
      hasGUI: true
    });

    // Times are in milliseconds
    this.start = params.start;
    this.end = params.end;

    this.loop = true;
    this.playing = false;

    this.tweens = {};
    this.objects = [];

    this.hasGUI = params.hasGUI;

    if (this.hasGUI) {
      Timeline.GUI.construct(this);
    }

  };

  _.extend(Timeline, {

    GUI: {

      construct: function(timeline) {

        var $el = $('<div class="timeline" />')
          .html(Timeline.GUI.template);

        _.each($el.find('.controls').children(), function(el) {
          $(el).bind('click', function(event) {
            var e = event.originalEvent;
            e.preventDefault();
            var action = el.className.replace(/\-.*$/, '');
            timeline[action]();
          });
        });

        // Export
        timeline.domElement = $el[0];

      },

      template: '<ul class="sidebar"> <li> <ul class="controls"> <li class="play"> <button>Play</button> </li> <li class="pause"> <button>Pause</button> </li> <li class="stop"> <button>Stop</button> </li> </ul> </li></ul><ul class="stage"></ul>',

      Tween: {

        construct: function(timeline, tween) {



        },

        // template: 

      },

      useDefaultStyles: function() {



      }

    }

  });

  _.extend(Timeline.prototype, {

    /**
     * Runtime functions
     */

    play: function() {

      if (!this.now) {
        this.now = this.start;
      }

      this.playing = true;
      return this;

    },

    pause: function() {

      this.playing = false;
      return this;

    },

    stop: function() {

      this.setTime(this.start);
      return this;

    },

    update: function(delta, forced) {

      if (!forced && (!this.playing || !delta)) {
        return this;
      }

      this.now = this.loop ? mod(this.now + delta, this.end - this.start) : this.now + delta;

      TWEEN.update(this.now);

      if (this.hasGUI) {
        this.updateGUI();
      }

    },

    setTime: function(t) {

      var time = Math.min(Math.max(t, this.start), this.end);

      this.update(time - this.now, true);

      return this;

    },

    /**
     * Setup functions
     */

    add: function(tween) {

      var parent = tween._object, name = parent.name, id = tween.id;

      if (!name) {
        name = parent.name = _.uniqueId('object-');
      }

      if (!id) {
        id = tween.id = _.uniqueId();
      }

      if (!parent.tweens) {
        parent.tweens = {};
      }

      // Figure out some kind of object-based hierarchy for grouping the tweens
      // in the UI of the timeline.

      this.tweens[tween.id] = parent.tweens[tween.id] = tween;

      if (_.indexOf(this.objects, parent) < 0) {
        this.objects.push(parent);
      }

      if (this.hasGUI) {

        Timeline.GUI.Tween.construct(timeline, tween);

      }

      return this;

    }

  });

  function clone(object) {
    var result = {};
    _.each(object, function(v, k) {
      if (_.isNumber(v)) {
        result[k] = parseFloat(v, 10);
      }
    });
    return result;
  }

  function mod(v, l) {
    while (v < 0) {
      v += l;
    }
    return v % l;
  }

})();