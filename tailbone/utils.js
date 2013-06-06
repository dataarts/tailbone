var reISO = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}(?:\.\d*)?)Z$/;

JSON._parse = JSON.parse;
JSON.parse = function(json) {return JSON._parse(json, function(key, value) {
    if (typeof value === 'string') {
      if (reISO.exec(value)) {
        return new Date(value);
      }
    }
    return value;
  });
};
if (jQuery !== undefined) {
  jQuery.parseJSON = JSON.parse;
  jQuery.ajaxSettings.converters["text json"] = JSON.parse;
}

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
http.HEAD = function(url, load, error, context) {
  $.ajax({
    type: 'HEAD',
    url: url,
    success: load,
    error: errorWrapper(error),
    context: context
  });
};
http.GET = function(url, load, error, context) {
  $.ajax({
    type: 'GET',
    url: url,
    success: load,
    error: errorWrapper(error),
    dataType: 'json',
    context: context
  });
};
http.POST = function(url, data, load, error, context) {
  $.ajax({
    type: 'POST',
    url: url,
    data: JSON.stringify(data),
    success: load,
    error: errorWrapper(error),
    dataType: 'json',
    contentType: 'application/json',
    context: context 
  });
};
http.DELETE = function(url, load, error, context) {
  $.ajax({
    type: 'DELETE',
    url: url,
    success: load,
    error: errorWrapper(error),
    dataType: 'json',
    context: context
  });
