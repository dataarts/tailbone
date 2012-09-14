/*
 * Bi-Directional data binding with AppEngine and the channel api
 */

window.tailbone = (function(window, document, undefined) {

function xhr(j,a,n) {
  var r = new XMLHttpRequest();
  if (r) {
    r.onreadystatechange = function() {
      if (r.readyState == 4) {
        (n||a)(JSON.parse(r.responseText));
      }
    };
    r.open(n ? "POST":"GET", j, !0);
    if (n) {
      r.setRequestHeader("Content-Type","application/json");
    }
    r.send(a);
  } else {
    throw Error("Browser does not support xhr. Try adding modernizer to polyfill.");
  }
}

Model = function() {
};

Model.query = function() {

};

/*
 * Dollar sign prefix names are ignored on the model as are underscore
 * _name
 * and
 * $name
 * are not included in the jsonifying of an object
 */
Model.prototype.$save = function() {

};

Model.prototype.$delete = function() {

};

// Add the channel js for appengine and bind the events.


// Exports
return {
  Model: Model
}

})(this, this.document);
