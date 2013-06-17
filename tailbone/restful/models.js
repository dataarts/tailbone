// This is a simple javascript wrapper to make using the restful api provided
// by tailbone easier.  It also includes bi-directional data binding with
// AppEngine and the channel api so that your javascript models upload in
// real time.


// Quering and Filtering
// ---------------------
// These are some useful helper functions for constructing queries, although you
// probably won't have to use these directly, see the query section below.

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
  var Model = function() {
  };

  // Get a model by its id.
  Model.get = function(id, opt_callback, opt_error) {
    var m = new Model();
    m.Id = id;
    m.$update(opt_callback, opt_error);
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
    setTimeout(function() {
      query.fetch(opt_callback);
    }, 0);
    // Bind to watch for changes to this model by others on the server.
    if (tailbone.databinding) {
      tailbone.bind(type, function() { query.fetch() });
    }
    return query;
  };

  // Helper function to serialize a model and strip any properties that match
  // the set of ignored prefixes or are of an unsupported type such as a
  // function.
  function serializeModel(model) {
    var obj = {};
    for (var member in model) {
      if (ignored_prefixes.indexOf(member[0]) < 0) {
        obj[member] = model[member];
      }
    }
    return obj;
  };

  // Save the model to the server.
  Model.prototype.$save = function(opt_callback, opt_error) {
    var model = this;
    http.POST('/api/' + type + '/', serializeModel(this), function(data) {
      for (var k in data) {
        model[k] = data[k];
      }
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

  // Update the model by fetching its latest value and overwriting the current
  // object.
  Model.prototype.$update = function(opt_callback, opt_error) {
    var model = this;
    http.GET('/api/' + type + '/' + this.Id, function(data) {
      for (var k in data) {
        model[k] = data[k];
      }
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
        _more = false,
        _reversed = false,
        _cursor = undefined,
        _query_cursor = undefined,
        _reverse_cursor = undefined;

    // Provide a projection of desired properties to the query
    query.projection = [];

    // the onchange callback
    query.onchange = undefined;

    function flip_order() {
      if (_order.length == 0) {
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
      } else {
        _query_cursor = _cursor;
      }
      return query.fetch(opt_callback);
    };

    query.__defineGetter__('more', function() { return _more; });

    query.__defineGetter__('page_size',
        function() { return _page_size; });
    query.__defineSetter__('page_size',
        function(page_size) {
          _page_size = page_size;
          query.fetch();
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
      if (_filter.length == 0) {
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

    // Actually fetches and updates the results in the query. This happens
    // automatically on a query so you shouldn't need this unless you want to
    // update the results this will fetch and update the current results.
    query.fetch = function(opt_callback) {
      function callback(data, status, xhr) {
        _cursor = xhr.getResponseHeader('cursor');
        _reverse_cursor = xhr.getResponseHeader('reverse-cursor');
        _more = JSON.parse(xhr.getResponseHeader('more'));
        query.splice(0, query.length);
        query.push.apply(query, data);
        var fn = opt_callback || query.onchange;
        if (fn) {
          fn(query);
        }
      }
      http.GET('/api/' + type + '/?params=' + query.serialize(), callback);
    };

    return query;
  };



  return Model;
};

// User is a built in model that is constructed like a normal model but has some
// additional functionality built in.
var User = new Model('users');

// Constructs a login url.
User.logout_url = function(redirect_url) {
  return '/api/login?url=' + (redirect_url || '/');
};

User.login_url = function(redirect_url) {
  return '/api/login?url=' + (redirect_url || '/');
};
