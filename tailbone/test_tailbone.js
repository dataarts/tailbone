var Todo = new tailbone.Model('todos');

function Counter(count, callback) {
  this.count = count - 1;
  this.callback = callback;
  var _this = this;
  function check() {
    if (_this.count <= 0) {
      clearInterval(poller);
      _this.callback();
    }
  }
  var poller = setInterval(check, 1000);
  return this;
}

asyncTest('Login', function() {

  var User = tailbone.User;

  var button = document.createElement('button');
  button.appendChild(document.createTextNode('Login Test'));
  button.onclick = function() {
    User.logout(function(resp) {
      User.get('me', null, function(d) {
        // ok(d.error == 'LoginError', d.error);
        User.login(function() {
          User.get('me', function(d) {
            ok(d.Id !== undefined, d.Id);
            document.body.removeChild(button);
            start();
          });
        });
      });
    });
  };
  document.body.appendChild(button);
});

asyncTest('List items', function() {
  var itemCount = 0;
  $.get('/api/todos/', function(d) {
    ok(d.length !== undefined, 'There is nothing in the database.');
    itemCount = d.length;
    start();
  });
});


asyncTest('Create model', function() {
  $.get('/api/todos/', function(d) {
    var itemCount = d.length;
    var todo = new Todo();
    todo.text = 'stuff';
    todo.$save(function() {
      $.get('/api/todos/', function(d) {
        ok(d.length == itemCount + 1, 'Expected ' + (itemCount + 1) +
          ' results got ' + itemCount);
        itemCount = d.length;
        start();
      });
    });
  });
});

asyncTest('Bind query', function() {
  $.get('/api/todos/', function(d) {
    var counter = new Counter(2, function() {
      ok(todos.length == itemCount, 'Got ' + todos.length +
        ' items, expected ' + itemCount);
      start();
    });
    var itemCount = d.length;
    var todos = Todo.query();
    ok(todos.length == 0, 'Should return immediately with 0.');
    todos.onchange = function() {
      counter.count -= 1;
    };
    var todo = new Todo();
    todo.text = 'stuff';
    todo.$save(function() {
      itemCount += 1;
    });
  });
});

asyncTest('Complex query', function() {
  $.get('/api/todos/?filter=count<3&filter=text==hi&order=count',
    function(d) {
    var itemCount = d.length;
    var counter = new Counter(6, function() {
      ok(todos.length == itemCount + 3, 'Got ' + todos.length +
        ' items, expected ' + (itemCount + 3));
      start();
    });
    for (var i = 0; i < 5; i++) {
      var todo = new Todo();
      todo.count = i;
      todo.text = 'hi';
      todo.$save();
    }
    var todos = Todo.query().filter('count <', 3).
      order('count').filter('text', '==', 'hi');
    todos.onchange = function() {
      counter.count -= 1;
    };
  });
});

function toBlob(data_url) {
  var d = atob(data_url.split(',')[1]);
  var b = new Uint8Array(d.length);
  for (var i = 0; i < d.length; i++) {
    b[i] = d.charCodeAt(i);
  }
  return new Blob([b], {type: 'image/png'});
}

asyncTest('Upload file', function() {
  var data = new FormData();
  var canvas = document.createElement('canvas');
  document.body.appendChild(canvas);
  var ctx = canvas.getContext('2d');
  ctx.fillRect(0, 0, 100, 100);
  var img = canvas.toDataURL();
  data.append('blob', toBlob(img), 'image');
  document.body.removeChild(canvas);
  $.get('/api/files', function(d) {
    console.log(d);
    $.ajax({
      type: 'POST',
      url: d.upload_url,
      data: data,
      cache: false,
      contentType: false,
      processData: false,
      success: function(items) {
        var d = items[0];
        ok(d.Id != undefined, 'Id is ' + d.Id);
        ok(d.size == 1616, 'size is ' + d.size);
        ok(d.content_type == 'image/png', 'content type is ' + d.content_type);
        start();
      }
    });
  });
});

asyncTest('User account', function() {
  var me = tailbone.User.get('me', function() {
    ok(me.Id != undefined, 'I have a signed in Id.');
    start();
  });
});
