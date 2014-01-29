// This is a simple javascript wrapper to make using the restful api provided
// by tailbone easier.  It also includes bi-directional data binding with
// AppEngine and the channel api so that your javascript models upload in
// real time.


// Quering and Filtering
// ---------------------
// These are some useful helper functions for constructing queries, although you
// probably won't have to use these directly, see the query section below.


// Emulate legacy getter/setter API using ES5 APIs.
// Since __defineGetter__ and __defineSetter__ are not supported any longer by IE9 or 10 or Windows 8, and Box2D for javascript v2.1a still uses them, this shim is required to run Box2D in those environments.
// This is taken directly from Allen Wirfs-Brock's blog at: 
// http://blogs.msdn.com/b/ie/archive/2010/09/07/transitioning-existing-code-to-the-es5-getter-setter-apis.aspx
try {
  if(!Object.prototype.__defineGetter__ &&
  Object.defineProperty({}, "x", { get: function() { return true } }).x) {
    Object.defineProperty(Object.prototype, "__defineGetter__",
   { enumerable: false, configurable: true,
    value: function(name, func) {
      Object.defineProperty(this, name,
       { get: func, enumerable: true, configurable: true });
    } 
   });
    Object.defineProperty(Object.prototype, "__defineSetter__",
   { enumerable: false, configurable: true,
    value: function(name, func) {
      Object.defineProperty(this, name,
       { set: func, enumerable: true, configurable: true });
    } 
   });
  }
} catch(defPropException) { /*Do nothing if an exception occurs*/ };
////////////////////////

function FILTER(name, opsymbol, value) {
  return [name, opsymbol, value];
}

function ORDER(name) {
  return name;
}

function AND() {
  var f = ['AND'];
  for (var i = 0; i < arguments.length; i++) {
    f.push(arguments[i]);
  }
  return f;
}

function OR() {
  var f = ['OR'];
  for (var i = 0; i < arguments.length; i++) {
    f.push(arguments[i]);
  }
  return f;
}


// This helps construct a model type which can be queried and created.
var Model = function(type, opt_schema) {
  var ignored_prefixes = ['_', '$'];


  // Model
  // -----
  // This is a model class for the particular type. This allows you to work with
  // your models directly in javascript and has several built in functions to
  // save them back to the server.
  var Model = function(defaults) {
    populate(this, defaults);
  };

  // Get a model by its id.
  Model.get = function(id, opt_callback, opt_error, opt_recurse) {
    var m = new Model();
    m.Id = id;
    m.$update(opt_callback, opt_error, opt_recurse);
    return m;
  };

  // Query generates a iterator for a query object. Queries inherit from the
  // native array type so all the ES5 iterators work on query objects, for
  // example:
  //
  //     var Todo = new tailbone.Model("todos");
  //     Todo.query(function(todos) {
  //       todos.forEach(function(v,i) {
  //         console.log(v,i);
  //       });
  //     });
  Model.query = function(opt_callback) {
    var query = new Query();
    // xhr query for collection with timeout to allow for chaining.
    //
    //     var results = Todo.query().filter("text =", "sample")
    query._queued = setTimeout(function() {
      query.fetch(opt_callback);
    }, 0);
    // Bind to watch for changes to this model by others on the server.
    if (tailbone.databinding) {
      tailbone.bind(type, function() { query.fetch(); });
    }
    return query;
  };

  // Helper function to serialize a model and strip any properties that match
  // the set of ignored prefixes or are of an unsupported type such as a
  // function.
  function serializeModel(model, submodel) {
    if (model instanceof Array) {
      var items = [];
      for(var i=0;i<model.length;i++) {
        items.push(serializeModel(model[i], true));
      }
      return items;
    } else if (model instanceof Date) {
      return model;
    } else if (model instanceof Object) {
      if (submodel) {
        for (var k in model) {
          if (k === '$class') {
            return model.Id;
          }
        }
      }
      var obj = {};
      for (var member in model) {
        if (ignored_prefixes.indexOf(member[0]) < 0) {
          obj[member] = serializeModel(model[member], true);
        }
      }
      return obj;
    } else {
      return model;
    }
  }

  // Save the model to the server.
  Model.prototype.$save = function(opt_callback, opt_error) {
    var model = this;
    http.POST('/api/' + type + '/', serializeModel(this), function(data) {
      populate(model, data);
      var fn = opt_callback || model.onchange;
      if (fn) {
        fn(model);
      }
      if (tailbone.databinding) {
        tailbone.trigger(type);
      }
    }, opt_error);
  };

  // Delete the model.
  Model.prototype.$delete = function(opt_callback, opt_error) {
    var model = this;
    http.DELETE('/api/' + type + '/' + this.Id, function() {
      var fn = opt_callback || model.onchange;
      if (fn) {
        fn();
      }
      if (tailbone.databinding) {
        tailbone.trigger(type);
      }
    }, opt_error);
  };

  function populate(model, data) {
    for (var k in data) {
      var obj = data[k];
      if (obj instanceof Array) {
        var items = [];
        for(var i=0;i<obj.length;i++) {
          var item = obj[i];
          if (item.$class) {
            var newModelClass = tailbone.Model(item.$class);
            var newModel = new newModelClass();
            populate(newModel, item);
            items.push(newModel);
          } else {
            populate(item, item);
            items.push(item);
          }
        }
        model[k] = items;
      } else if (obj instanceof Date) { 
        model[k] = obj;
      } else if (obj instanceof Object) {
        if (obj.$class) {
          var newModelClass = tailbone.Model(obj.$class);
          var newModel = new newModelClass();
          populate(newModel, obj);
          model[k] = newModel;
        } else {
          populate(obj, obj);
          model[k] = obj;
        }
      } else {
        model[k] = obj;
      }
    }
  }

  // Update the model by fetching its latest value and overwriting the current
  // object.
  Model.prototype.$update = function(opt_callback, opt_error, opt_recurse) {
    var model = this;
    var opts = '';
    if (opt_recurse) {
      opts = '?recurse=true';
    }
    http.GET('/api/' + type + '/' + this.Id + opts, function(data) {
      populate(model, data);
      var fn = opt_callback || model.onchange;
      if (fn) {
        fn(model);
      }
    }, opt_error);
  };


  // Query
  // -----
  // Query is an iterable collection of a Model.
  var Query = function() {
    var query = [],
        _filter = [],
        _order = [],
        _page_size = 100,
        _has_next = false,
        _has_previous = false,
        _reversed = false,
        _recurse = false,
        _cursor = undefined,
        _query_cursor = undefined,
        _reverse_cursor = undefined;

    // Provide a projection of desired properties to the query
    query.projection = [];

    // the onchange callback
    query.onchange = undefined;

    function flip_order() {
      if (_order.length === 0) {
        _order = ['-key'];
      } else {
        for(var i=0,l=_order.length;i<l;++i) {
          if (_order[i][0] == '-') {
            _order[i] = _order[i].substring(1);
          } else {
            _order[i] = '-' + _order[i];
          }
        }
      }
    }

    query.next = function(opt_callback) {
      if(_reversed) {
        flip_order();
        _reversed = false;
        _query_cursor = _reverse_cursor;
        var _prev_page_size = _page_size;
        _page_size = this.length;
        query.fetch(function() {
          _query_cursor = _cursor;
          _page_size = _prev_page_size;
          query.fetch(opt_callback);
        });
        return this;
      } else {
        _query_cursor = _cursor;
      }
      return query.fetch(opt_callback);
    };

    query.previous = function(opt_callback) {
      // TODO: need to reverse the order of the filters and user reverse-cursor
      if(!_reversed) {
        flip_order();
        _reversed = true;
        _query_cursor = _reverse_cursor;
        var _prev_page_size = _page_size;
        _page_size = this.length;
        query.fetch(function() {
          _query_cursor = _cursor;
          _page_size = _prev_page_size;
          query.fetch(opt_callback);
        });
        return this;
      } else {
        _query_cursor = _cursor;
      }
      return query.fetch(opt_callback);
    };

    query.__defineGetter__('more', function() {
      if(window.console) {
        console.warn('"more" is deprecated please use "has_next"');
      }
      return _has_next;
    });
    query.__defineGetter__('has_next', function() { return _has_next; });
    query.__defineGetter__('has_previous', function() { return _has_previous; });

    query.__defineGetter__('page_size',
        function() { return _page_size; });
    query.__defineSetter__('page_size',
        function(page_size) {
          _page_size = page_size;
          if (!query._queued) {
            query.fetch();
          }
        });

    // Filter the query results. This can either be a constructed filter using one
    // of the provided functions like
    // AND(FILTER("name","=","value"), FILTER("other","=","value")). Or you can
    // construct a filter in place with the shorthand. filter("name","=","value")
    // or filter("name =", "value")
    query.filter = function() {
      var filter;
      switch (arguments.length) {
        case 1:
          filter = arguments[0];
          break;
        case 2:
          filter = FILTER.apply(this,
              arguments[0].split(' ').concat(arguments[1]));
          break;
        case 3:
          filter = FILTER.apply(this, arguments);
          break;
        default:
          throw Error('Undefined FILTER format.');
      }
      if (_filter.length === 0) {
        _filter = ['AND'];
      }
      _filter.push(filter);
      return this;
    };

    // Order the query results. add a - in front of the name to make it sort
    // descending.
    query.order = function(name) {
      _order.push(ORDER(name));
      return this;
    };

    // Simple serialization and jsonification of the query so it can be passed to
    // the server.
    query.serialize = function() {
      return JSON.stringify({
        filter: _filter,
        order: _order,
        cursor: _query_cursor,
        projection: this.projection,
        page_size: _page_size
      });
    };

    query.recurse = function(value) {
      if (value === undefined) {
        _recurse = true;
      } else {
        _recurse = !!value;
      }
      return this;
    };

    // Actually fetches and updates the results in the query. This happens
    // automatically on a query so you shouldn't need this unless you want to
    // update the results this will fetch and update the current results.
    query.fetch = function(opt_callback) {
      function callback(data, status, xhr) {
        query._queued = undefined;
        var more = JSON.parse(xhr.getResponseHeader('more'));
        if (_reversed) {
          _has_next = true;
          _has_previous = more;
        } else {
          _has_previous = _query_cursor;
          _has_next = more;
        }
        _cursor = xhr.getResponseHeader('cursor');
        _reverse_cursor = xhr.getResponseHeader('reverse-cursor');
        query.splice(0, query.length);
        if (_reversed) {
          data.reverse();
        }
        for (var i=0;i<data.length;i++) {
          var item = data[i];
          var model = new Model();
          populate(model, data[i]);
          query.push.call(query, model);
        }
        var fn = opt_callback || query.onchange;
        if (fn) {
          fn(query);
        }
      }
      var recurse = '';
      if (_recurse) {
        recurse = '&recurse=true';
      }
      http.GET('/api/' + type + '/?params=' + query.serialize() + recurse, callback);
    };

    return query;
  };



  return Model;
};

// User is a built in model that is constructed like a normal model but has some
// additional functionality built in.
var User = new Model('users');
