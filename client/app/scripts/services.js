'use strict';

todoApp.factory('Todo', function($resource) {
  return $resource("http://localhost:port/api/todos/:id",
                   {id: "@Id", port: ":8080"});
});
