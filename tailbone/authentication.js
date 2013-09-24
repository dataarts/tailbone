function processResponse(callback) {
  var pt = function(message) {
    window.removeEventListener('message', pt);
    var localhost = false;
    if (message.origin.match("localhost")) {
      localhost = true;
    }
    if (!localhost && message.origin !== ( window.location.protocol + "//" + window.location.host )) {
      throw new Error('Origin does not match.');
    } else {
      if (typeof callback === 'function') {
        callback(message);
      }
    }
  };
  return pt;
}

function login(callback) {
  var options = Array.prototype.slice.apply(arguments);
  options = options.slice(1) || [];
  window.addEventListener('message', processResponse(callback), false);
  options.unshift('/api/login?continue=/api/logup');
  window.open.apply(window, options);
};

function logout(callback) {
  authorized.user = undefined;
  http.GET('/api/logout?continue=/api/logup', callback);
};

function authorized(callback) {
  if (typeof callback !== 'function') {
    if (window.console) {
      console.warn('authorize called without callback defined.');
    }
    return;
  }
  var options = Array.prototype.slice.apply(arguments);
  options = options.slice(1) || [];
  if (authorized.user) {
    callback(authorized.user);
  }
  http.GET('/api/users/me', function(user) {
    authorized.user = user;
    callback(authorized.user);
  }, function() {
    options.unshift(function() {
      http.GET('/api/users/me', function(user) {
        authorized.user = user;
        callback(authorized.user);
      });
    });
    login.apply(this, options);
  });
};

// Constructs a login url.
function logout_url(redirect_url) {
  return '/api/login?url=' + (redirect_url || '/');
};

function login_url(redirect_url) {
  return '/api/login?url=' + (redirect_url || '/');
};