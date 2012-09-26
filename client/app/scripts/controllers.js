'use strict';

todoApp.controller('ListCtrl', function($scope, Todo) {
  // $scope.todos = Todo.query(backbone.AND(backbone.FILTER("stuff","==",33),
  //                                        backbone.FILTER("name", "!=", "doug")),
  //                           backbone.ORDER("stuff"));
  // $scope.todos = Todo.query();
  // $scope.todos = Todo.query().filter("name","==",44).filter("name","!=","32").order("33");
  // $scope.todos = Todo.query({
  //                         "filter": [
  //                                     ["name","==","myname","other","!=","32"],
  //                                     ["name","==","myname", [["other","==","stuff"],["other","==","thing"]]]
  //                                   ],
  //                         "order": ["name","-other"]
  //                         });
  // // explicative type
  // $scope.todos = Todo.query("/api/todos?filter=name==33!str")
  $scope.todos = Todo.query();
  $scope.add = function() {
    var newTodo = new Todo();
    newTodo.text = Math.random() + ' some text';
    newTodo.stuff = {"thiny": Math.random()*100};
    newTodo.$save();
    // $scope.todos = Todo.query();
    $scope.todos.push(newTodo);
  };
});

todoApp.controller('ItemCtrl', function($scope, Todo) {

});
