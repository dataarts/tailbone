var Todo = new tailbone.Model('todos');

var itemCount = 0;

test('List items', function() {
  stop();
  tailbone.http.GET('/api/todos/', function(d) {
    ok(d.length >= 0, 'Can query for todos');
    itemCount = d.length;
    start();
  });
});


test('Create model', function() {
  stop();
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

test('Bind query', function() {
  stop();
  var todos = Todo.query();
  ok(todos.length == 0, 'Should return immediately with 0.');
  todos.onchange = function() {
    ok(todos.length == itemCount, 'Got ' + todos.length +
      ' items, expected ' + itemCount);
    todos.onchange = function() {
      itemCount = itemCount + 1;
      ok(todos.length == itemCount, 'Got ' + todos.length +
        ' items, expected ' + itemCount);
      start();
    };
    var todo = new Todo();
    todo.text = 'stuff';
    todo.$save();
  };
});
