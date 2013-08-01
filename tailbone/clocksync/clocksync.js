//https://github.com/ffdead/clocksync

// Simple Time sync helper class

/*

  Time synchronization protocol for networked clients
 
  Example usage:
 
    // setup a sync method using ajax (or websockets etc)
    // use clocksync.data() to generate the data needed to send to the server
    // handle server response to clocksync.syncResponse
    clocksync.syncMethod = function () {
      $.post('/sync', clocksync.data(), clocksync.syncResponse, 'text');
    }

    // sync
    clocksync.sync(function (now, delta) {
      console.log('obtained synched time:', now, ' local delta: ', delta);
    });
 

  Algorithm (http://www.mine-control.com/zack/timesync/timesync.html):
   1. Client stamps current local time on a "time request" packet and sends to
      server
   2. Upon receipt by server, server stamps server-time and returns
   3. Upon receipt by client,
   4. The first result should immediately be used to update the clock since it
      will get the local clock into at least the right ballpark (at least the 
      right timezone!)
   5. The client repeats steps 1 through 3 five or more times, pausing a few 
      seconds each time. Other traffic may be allowed in the interim, but 
      should be minimized for best results
   6. The results of the packet receipts are accumulated and sorted in lowest
      -latency to highest-latency order. The median latency is determined by 
      picking the mid-point sample from this ordered list.
   7. All samples above approximately 1 standard-deviation from the median are 
      discarded and the remaining samples are averaged using an arithmetic mean.
*/

  var samples = [],
      clockDelta = 0;

  var now;
  if (window.performance && performance.now) {
    now = function() {
      return performance.timing.navigationStart + performance.now();
    };
  } else {
    now = function() {
      return +new Date();
    };
  }

  var nowsync = function () {
    return now() - clockDelta;
  };

  var createSyncData = function () {
    return {clientLocalTime: now()};
  };

  var handleSyncResponse = function (data) {
    var receiveTime = now();
    if (typeof(data) === 'string') {
      data = JSON.parse(data);
    }
    data.receiveTime = receiveTime;
    data.latency = (data.receiveTime - data.clientLocalTime) * 0.5;
    data.clockDelta = data.receiveTime - data.serverLocalTime - data.latency;
    updateSync(data);
  };

  var updateSync = function (sample) {
    clockDelta = sample.clockDelta;
    pushSample(sample);
    if (samples.length < 9) {
      return setTimeout(clocksync.syncMethod, 100);
    }
    completeSync();
  };

  var completeSync = function () {
    var list = filterSamples(samples);
    clockDelta = getAverageClockDelta(list);
    if (clocksync.callback) {
      clocksync.callback(nowsync(), clockDelta);
    }
  };

  var pushSample = function (sample) {
    var i, len = samples.length;

    for(i = 0; i < len; i++) {
      if (sample.latency < samples[i].latency) {
        samples.splice(i, 0, sample);
        return;
      }
    }
    samples.push(sample);
  };

  var calcMedian = function (values) {
    var half = Math.floor(values.length/2);
    if(values.length % 2) {
      return values[half];
    } else {
      return (values[half-1] + values[half]) / 2.0;
    }
  };

  var filterSamples = function (samples) {
    var list = [],
        i,
        latency,
        len = samples.length,
        sd = getStandardDeviation(samples),
        median = calcMedian(samples);

    for (i=0; i < len; i++) {
      latency = samples[i].latency;
      if (latency > median.latency - sd && latency < median.latency + sd) {
        list.push(samples[i]);
      }
    }

    return list;
  };

  var getAverageClockDelta = function (samples) {
    var i = samples.length,
        sum = 0;
    while( i-- ){
      sum += samples[i].clockDelta;
    }
    return sum / samples.length;
  };



  // http://bateru.com/news/2011/03/javascript-standard-deviation-variance-average-functions/
  var isArray = function (obj) {
    return Object.prototype.toString.call(obj) === "[object Array]";
  },
  getNumWithSetDec = function( num, numOfDec ){
    var pow10s = Math.pow( 10, numOfDec || 0 );
    return ( numOfDec ) ? Math.round( pow10s * num ) / pow10s : num;
  },
  getAverageFromNumArr = function( numArr, numOfDec ){
    if( !isArray( numArr ) ){ return false; }
    var i = numArr.length,
      sum = 0;
    while( i-- ){
      sum += numArr[ i ].latency;
    }
    return getNumWithSetDec( (sum / numArr.length ), numOfDec );
  },
  getVariance = function( numArr, numOfDec ){
    if( !isArray(numArr) ){ return false; }
    var avg = getAverageFromNumArr( numArr, numOfDec ),
      i = numArr.length,
      v = 0;

    while( i-- ){
      v += Math.pow( (numArr[ i ].latency - avg), 2 );
    }
    v /= numArr.length;
    return getNumWithSetDec( v, numOfDec );
  },
  getStandardDeviation = function( numArr, numOfDec ){
    if( !isArray(numArr) ){ return false; }
    var stdDev = Math.sqrt( getVariance( numArr, numOfDec ) );
    return getNumWithSetDec( stdDev, numOfDec );
  };


var ajaxSyncMethod = function() {
  var xhr = new XMLHttpRequest();
  xhr.open('HEAD', '/api/clocksync', false);
  var start = Date.now();
  xhr.onreadystatechange = function(e) {
    if (xhr.readyState === xhr.DONE) {
      var server_time = parseFloat(xhr.getResponseHeader('Last-Modified'));
      clocksync.syncResponse({
        clientLocalTime: start,
        serverLocalTime: server_time
      });
    }
  };
  xhr.send();
};

var clocksync = {
  delta: clockDelta,
  time: nowsync,
  sync: function(callback) {
    this.callback = callback;
    this.syncMethod();
  },
  syncMethod: ajaxSyncMethod,
  data: createSyncData,
  syncResponse: handleSyncResponse
};



