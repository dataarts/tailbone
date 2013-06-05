// Simple Time sync helper class


var current_time;
if (performance && performance.now && performance.timing) {
  current_time = function(significant) {
    return performance.timing.connectStart + performance.now();
  };
} else {
  current_time = function(significant) {
    return Date.now();
  };
}
current_time = Date.now;

function TimeStats() {
  this.latency = [];
  this.diff = 0;
  this.bufferSize = 20;
  this.avglatency = 0;
}

TimeStats.prototype.sync = function(server_time, transport) {
  this.latency.unshift(transport);
  var len = this.latency.length;
  this.latency = this.latency.slice(len - this.bufferSize, len);
  this.latency.sort(function(a,b) { return a-b; });
  var midpoint = Math.floor(len/2);
  var median = this.latency[midpoint];
  this.latency.sort(function(a,b) {
    return Math.abs(a-median) - Math.abs(b-median);
  });
  var avg = this.latency.slice(0, midpoint+1);
  this.avglatency = avg.reduce(function(a,b){ return a+b; }) / avg.length;
  // update avg latency
  this.syncedAt = current_time();
  var diff = ((server_time + this.avglatency) - this.syncedAt);
  var delta = Math.abs(diff - this.diff);
  if (len === this.bufferSize && delta >= this.delta) {
    // we have stopped improving
    return true;
  }
  console.log(60000-diff, 'diff', diff, 'delta', delta);
  this.diff = diff;
  this.delta = delta;
  return false;
};

function syncwebsocket(time, timeserver) {
  time._stats.latency = [];
  var _onmessage = timeserver.onmessage;
  var start = 0;
  timeserver.onmessage = function(message) {
    if (message[0] === 't') {
      var transport = (current_time() - start) / 2;
      var server_time = parseFloat(message.substring(1));
      var synced = time._stats.sync(server_time, transport);
      time._diff = time._stats.diff;
      if (synced) {
        clearInterval(synchronizer);
        // reset onmessage
        timeserver.onmessage = _onmessage;
        // setup a future time to check again
        setTimeout(function() {
          syncwebsocket(time, timeserver);
        }, 60000);
      }
      return;
    }
    if (_onmessage) {
      _onmessage.call(timeserver, message);
    }
  };
  // sync time
  var synchronizer = setInterval(function() {
    start = current_time();
    timeserver.send('t');
  }, 1000);
}

function syncajax(time, timeserver) {
  time._stats.latency = [];
  console.log('syncajax');
  var synchronizer = setInterval(function() {
    console.log('interval');
    var xhr = new XMLHttpRequest();
    xhr.open('HEAD', timeserver, false);
    var start = current_time();
    xhr.onreadystatechange = function(e) {
      if (xhr.readyState === xhr.DONE) {
        var transport = (start - current_time()) / 2;
        var server_time = parseFloat(xhr.getResponseHeader('Current-Time'));
        console.log('end', server_time, current_time());
        var synced = time._stats.sync(server_time, transport);
        time._diff = time._stats.diff;
        if (synced) {
          clearInterval(synchronizer);
          // setup a future time to check again
          setTimeout(function() {
            syncajax(time, timeserver);
          }, 60000);
        }
      }
    };
    xhr.send();
  }, 1000);
}

function Time(timeserver) {
  this._diff = 0;
  this._stats = new TimeStats();

  if (timeserver instanceof WebSocket) {
    // websocket timer
    syncwebsocket(this, timeserver);
  } else if (typeof(timeserver) === 'string') {
    // ajax get
    syncajax(this, timeserver);
  }
}

Time.prototype.now = function() {
  return current_time() + time._diff;
};

// milliseconds till next time_window farther away than min_future (default: 0)
Time.prototype.next = function(time_window, min_future) {

};

