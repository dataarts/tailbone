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
if (window.jQuery !== undefined) {
  jQuery.parseJSON = JSON.parse;
  jQuery.ajaxSettings.converters["text json"] = JSON.parse;
}

})();

var http = {};
(function() {

function json_request(kind, url, success, error, context) {
  var xhr;
  if (XMLHttpRequest) { 
    xhr = new XMLHttpRequest();
  } else {
    xhr = new ActiveXObject("Microsoft.XMLHTTP");
  }
  xhr.open(kind, url, true);
  xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
  xhr.setRequestHeader("If-None-Match", "some-random-string");
  xhr.setRequestHeader("Cache-Control", "no-cache,max-age=0");
  xhr.setRequestHeader("Pragma", "no-cache");

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

})();
