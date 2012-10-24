

var Todo = new tailbone.Model('todos');

asyncTest('List items', function() {
  var itemCount = 0;
  tailbone.http.GET('/api/todos/', function(d) {
    ok(d.length !== undefined, 'There is nothing in the database.');
    itemCount = d.length;
    start();
  });
});


asyncTest('Create model', function() {
  tailbone.http.GET('/api/todos/', function(d) {
    var itemCount = d.length;
    var todo = new Todo();
    todo.text = 'stuff';
    todo.$save(function() {
      tailbone.http.GET('/api/todos/', function(d) {
        ok(d.length == itemCount + 1, 'Has results in the database.');
        itemCount = d.length;
        start();
      });
    });
  });
});

asyncTest('Bind query', function() {
  tailbone.http.GET('/api/todos/', function(d) {
    var itemCount = d.length;
    var todos = Todo.query();
    ok(todos.length == 0, 'Should return immediately with 0.');
    todos.onchange = function() {
      console.log('todos', todos.length);
    };
    var todo = new Todo();
    todo.text = 'stuff';
    todo.$save(function() {
      itemCount += 1;
    });
    setTimeout(function() {
      ok(todos.length == itemCount, 'Got ' + todos.length +
        ' items, expected ' + itemCount);
      start();
    }, 1000);
  });
});

test('Complex query', function() {
  ok(1 == 1, 'reality');
});

asyncTest('User account', function() {
  var me = tailbone.User.get('me', function() {
    ok(me.Id != undefined, 'I have a signed in Id.');
    start();
  });
});
