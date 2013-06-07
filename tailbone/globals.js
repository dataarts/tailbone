// globals.js 
// TODO: need a better way to handle this with proper dependency managment with multiple imports

(function() {

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

})();

// Should probably just use jquery but put this here if you don't
// TODO: need a better fix for how to handle ajax
var http = {};
(function() {

if (jQuery !== undefined) {

function errorWrapper(fn) {
  if (typeof fn === 'function') {
    return function(jqXHR, textStatus, errorThrown) {
      var data = jqXHR.responseText;
      try { data = JSON.parse(data); } catch(e) {}
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
};

} else {

function json_request(kind, url, success, error, context) {
  var xhr;
  if (XMLHttpRequest) { 
    xhr = new XMLHttpRequest();
  } else {
    xhr = new ActiveXObject("Microsoft.XMLHTTP");
  }
  xhr.open(kind, url, true);
  xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
  xhr.onreadystatechange = function() {
    if (xhr.readyState === 4) {
      var data = xhr.responseText;
      try { data = JSON.parse(data); } catch(e) {}
      var args = Array.prototype.slice.call(arguments);
      args.unshift(data);
      args.push(xhr);
      if (xhr.status === 200 && typeof success === 'function') {
        success.apply(context || xhr, args);
      } else if (typeof error === 'function') {
        error.apply(context || xhr, args);
      } else {
        if (console) {
          console.warn('Made Ajax request but set no callback.');
        }
      }
    }
  };
  return xhr;
}
http.HEAD = function(url, load, error, context) {
  xhr = json_request('HEAD', url, load, error, context);
  xhr.send();
};
http.GET = function(url, load, error, context) {
  xhr = json_request('GET', url, load, error, context);
  xhr.send();
};
http.POST = function(url, data, load, error, context) {
  xhr = json_request('POST', url, load, error, context);
  xhr.send(JSON.stringify(data));
};
http.DELETE = function(url, load, error, context) {
  xhr = json_request('DELETE', url, load, error, context);
  xhr.send();
};

}
})();
