'use strict';

todoApp.controller('ListCtrl', function($scope, Todo) {
  $scope.todos = Todo.query();
  $scope.add = function() {
    var newTodo = new Todo();
    newTodo.text = Math.random() + ' some text';
    newTodo.$save();
    // $scope.todos = Todo.query();
    $scope.todos.push(newTodo);
  };
});

todoApp.controller('ItemCtrl', function($scope, Todo) {

});
