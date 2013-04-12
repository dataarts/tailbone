'use strict';

// Override json parsing and loading to handle dates
// provide base wrapper for jquery ajax convience functions

window.tailbone = !window.tailbone ? {} : window.tailbone;

(function() {

var reISO = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}(?:\.\d*)?)Z$/;

JSON._parse = JSON.parse;
JSON.parse = function(json) {
  return JSON._parse(json, function(key, value) {
    if (typeof value === 'string') {
      if (reISO.exec(value)) {
        return new Date(value);
      }
    }
    return value;
  });
};

// Since all of this is ajax there is a simple wrapper around $.ajax.
// If you don't have jQuery already on your site you will need to install
// it or provide your own global function that has the same api and bind
// it to $.ajax (for example you could use zepto.js but since
// jQuery is cached in most browsers I would just point
// to the google jQuery CDN)
var http = {};
function errorWrapper(fn) {
  if (fn) {
    return function(jqXHR, textStatus, errorThrown) {
      var data;
      try {
        data = JSON.parse(jqXHR.responseText);
      } catch (e) { }
      fn(data, textStatus, jqXHR, errorThrown);
    }
  }
}
http.GET = function(url, load, error) {
  $.ajax({
    type: 'GET',
    url: url,
    success: load,
    error: errorWrapper(error),
    dataType: 'json'
  });
};
http.POST = function(url, data, load, error) {
  $.ajax({
    type: 'POST',
    url: url,
    data: JSON.stringify(data),
    success: load,
    error: errorWrapper(error),
    dataType: 'json',
    contentType: 'application/json'
  });
};
http.DELETE = function(url, load, error) {
  $.ajax({
    type: 'DELETE',
    url: url,
    success: load,
    error: errorWrapper(error),
    dataType: 'json'
  });
};

// export http service for convience
window.http = http;

})();
