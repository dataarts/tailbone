/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/4/13
 * Time: 3:02 AM
 */

// Polyfills  https://code.google.com/p/webrtc/source/browse/trunk/samples/js/base/adapter.js
var RTCPeerConnection = null;
var getUserMedia = null;
var attachMediaStream = null;
var reattachMediaStream = null;
var webrtcDetectedBrowser = null;
var webrtcDetectedVersion = null;

function trace(text) {
  // This function is used for logging.
  if (text[text.length - 1] == '\n') {
    text = text.substring(0, text.length - 1);
  }
  console.log((performance.now() / 1000).toFixed(3) + ": " + text);
}

if (navigator.mozGetUserMedia) {
  console.log("This appears to be Firefox");

  webrtcDetectedBrowser = "firefox";

  webrtcDetectedVersion =
                  parseInt(navigator.userAgent.match(/Firefox\/([0-9]+)\./)[1]);

  // The RTCPeerConnection object.
  RTCPeerConnection = mozRTCPeerConnection;

  // The RTCSessionDescription object.
  RTCSessionDescription = mozRTCSessionDescription;

  // The RTCIceCandidate object.
  RTCIceCandidate = mozRTCIceCandidate;

  // Get UserMedia (only difference is the prefix).
  // Code from Adam Barth.
  getUserMedia = navigator.mozGetUserMedia.bind(navigator);

  // Creates iceServer from the url for FF.
  createIceServer = function(url, username, password) {
    var iceServer = null;
    var url_parts = url.split(':');
    if (url_parts[0].indexOf('stun') === 0) {
      // Create iceServer with stun url.
      iceServer = { 'url': url };
    } else if (url_parts[0].indexOf('turn') === 0 &&
               (url.indexOf('transport=udp') !== -1 ||
                url.indexOf('?transport') === -1)) {
      // Create iceServer with turn url.
      // Ignore the transport parameter from TURN url.
      var turn_url_parts = url.split("?");
      iceServer = { 'url': turn_url_parts[0],
                    'credential': password,
                    'username': username };
    }
    return iceServer;
  };

  // Attach a media stream to an element.
  attachMediaStream = function(element, stream) {
    console.log("Attaching media stream");
    element.mozSrcObject = stream;
    element.play();
  };

  reattachMediaStream = function(to, from) {
    console.log("Reattaching media stream");
    to.mozSrcObject = from.mozSrcObject;
    to.play();
  };

  // Fake get{Video,Audio}Tracks
  MediaStream.prototype.getVideoTracks = function() {
    return [];
  };

  MediaStream.prototype.getAudioTracks = function() {
    return [];
  };
} else if (navigator.webkitGetUserMedia) {
  console.log("This appears to be Chrome");

  webrtcDetectedBrowser = "chrome";
  webrtcDetectedVersion =
             parseInt(navigator.userAgent.match(/Chrom(e|ium)\/([0-9]+)\./)[2]);

  // Creates iceServer from the url for Chrome.
  createIceServer = function(url, username, password) {
    var iceServer = null;
    var url_parts = url.split(':');
    if (url_parts[0].indexOf('stun') === 0) {
      // Create iceServer with stun url.
      iceServer = { 'url': url };
    } else if (url_parts[0].indexOf('turn') === 0) {
      if (webrtcDetectedVersion < 28) {
        // For pre-M28 chrome versions use old TURN format.
        var url_turn_parts = url.split("turn:");
        iceServer = { 'url': 'turn:' + username + '@' + url_turn_parts[1],
                      'credential': password };
      } else {
        // For Chrome M28 & above use new TURN format.
        iceServer = { 'url': url,
                      'credential': password,
                      'username': username };
      }
    }
    return iceServer;
  };

  // The RTCPeerConnection object.
  RTCPeerConnection = webkitRTCPeerConnection;

  // Get UserMedia (only difference is the prefix).
  // Code from Adam Barth.
  getUserMedia = navigator.webkitGetUserMedia.bind(navigator);

  // Attach a media stream to an element.
  attachMediaStream = function(element, stream) {
    if (typeof element.srcObject !== 'undefined') {
      element.srcObject = stream;
    } else if (typeof element.mozSrcObject !== 'undefined') {
      element.mozSrcObject = stream;
    } else if (typeof element.src !== 'undefined') {
      element.src = URL.createObjectURL(stream);
    } else {
      console.log('Error attaching stream to element.');
    }
  };

  reattachMediaStream = function(to, from) {
    to.src = from.src;
  };

  // The representation of tracks in a stream is changed in M26.
  // Unify them for earlier Chrome versions in the coexisting period.
  if (!webkitMediaStream.prototype.getVideoTracks) {
    webkitMediaStream.prototype.getVideoTracks = function() {
      return this.videoTracks;
    };
    webkitMediaStream.prototype.getAudioTracks = function() {
      return this.audioTracks;
    };
  }

  // New syntax of getXXXStreams method in M26.
  if (!webkitRTCPeerConnection.prototype.getLocalStreams) {
    webkitRTCPeerConnection.prototype.getLocalStreams = function() {
      return this.localStreams;
    };
    webkitRTCPeerConnection.prototype.getRemoteStreams = function() {
      return this.remoteStreams;
    };
  }
} else {
  console.log("Browser does not appear to be WebRTC-capable");
}


var DATA_CHANNEL_CONFIG = {
  optional: [{RtpDataChannels: true},
             {DtlsSrtpKeyAgreement: true}]
};

var DATA_CHANNEL_SUPPORTED = (function() {
  try {
    // raises exception if createDataChannel is not supported
    var pc = new RTCPeerConnection({iceServers: []},
                   DATA_CHANNEL_CONFIG);
    var channel = pc.createDataChannel('supportCheck', {
    reliable: false
    });
    channel.close();
    return true;
  } catch (e) {
    return false;
  }
})();

var BANDWIDTH = 64; // 64 kbps

var RTCChannelUtils = {

  defaultIceServers: function(channel) {
    var ice = [];
    if (navigator.mozGetUserMedia) {
      ice.push(createIceServer('stun:23.21.150.121'))
    } else {
      var opts = channel.localNode.mesh.options;
      if (opts.turn) {
        ice.push(createIceServer(opts.turn, opts.username, opts.password))
      }
      ice.push(createIceServer('stun:stun.l.google.com:19302'))
    }
    return ice;
  },

  highBandwidth: function(sdp, bandwidth) {
    bandwidth = bandwidth || BANDWIDTH;
    sdp = sdp.replace('b=AS:30', 'b=AS:' + bandwidth);
    return sdp;
  },

  preferOpus: function (sdp) {
    var sdpLines = sdp.split('\r\n'),
      mLineIndex,
      i;

    for (i = 0; i < sdpLines.length; i++) {
      if (sdpLines[i].search('m=audio') !== -1) {
        mLineIndex = i;
        break;
      }
    }
    if (mLineIndex === null) {
      return sdp;
    }

    for (i = 0; i < sdpLines.length; i++) {
      if (sdpLines[i].search('opus/48000') !== -1) {
        var opusPayload = RTCChannelUtils.extractSdp(sdpLines[i], /:(\d+) opus\/48000/i);
        if (opusPayload) {
          sdpLines[mLineIndex] = RTCChannelUtils.setDefaultCodec(sdpLines[mLineIndex], opusPayload);
        }
        break;
      }
    }

    sdpLines = RTCChannelUtils.removeCN(sdpLines, mLineIndex);
    sdp = sdpLines.join('\r\n');

    return sdp;
  },

  extractSdp: function (sdpLine, pattern) {
    var result = sdpLine.match(pattern);
    return (result && result.length == 2) ? result[1] : null;
  },

  setDefaultCodec: function (mLine, payload) {
    var elements = mLine.split(' ');
    var newLine = [];
    var index = 0;

    for (var i = 0; i < elements.length; i++) {
      if (index === 3) {
        newLine[index++] = payload;
      }
      if (elements[i] !== payload) {
        newLine[index++] = elements[i];
      }
    }

    return newLine.join(' ');
  },

  removeCN : function (sdpLines, mLineIndex) {
    var mLineElements = sdpLines[mLineIndex].split(' ');
    for (var i = sdpLines.length-1; i >= 0; i--) {
      var payload = RTCChannelUtils.extractSdp(sdpLines[i], /a=rtpmap:(\d+) CN\/\d+/i);
      if (payload) {
        var cnPos = mLineElements.indexOf(payload);
        if (cnPos !== -1) {
          mLineElements.splice(cnPos, 1);
        }
        sdpLines.splice(i, 1);
      }
    }

    sdpLines[mLineIndex] = mLineElements.join(' ');
    return sdpLines;
  },

  createPeerConnection: function(channel) {
    var pc = new RTCPeerConnection({iceServers: RTCChannelUtils.defaultIceServers(channel)},
                   DATA_CHANNEL_CONFIG);
    channel.pc = pc;

    pc.onicecandidate = function (event) {
      if (event.candidate) {
        channel.remoteNode._trigger('rtc_iceCandidate', event.candidate);
      }
    };

    pc.onconnecting = function (event) {
      console.log('onConnecting', event);
    };

    pc.onopen = function (event) {
      console.log('onOpen', event);
    };

    pc.onaddstream = function (event) {
      console.log('add stream', event);
    };

    pc.ondatachannel = function (event) {
      console.log('add data channel???', event);
      // RTCChannelUtils.addDataChannel(channel, event.channel); 
    };

  },

  sendOffer: function(channel) {
    channel.pc.createOffer(function (desc) {
      desc.sdp = RTCChannelUtils.preferOpus(desc.sdp);
      desc.sdp = RTCChannelUtils.highBandwidth(desc.sdp);
      channel.pc.setLocalDescription(desc);
      channel.remoteNode._trigger('rtc_offer', desc);
    }, function () {
      console.log('createOffer error');
    });
  },

  sendAnswer: function(channel) {
    channel.pc.createAnswer(function(desc) {
      desc.sdp = RTCChannelUtils.preferOpus(desc.sdp);
      desc.sdp = RTCChannelUtils.highBandwidth(desc.sdp);
      channel.pc.setLocalDescription(desc);
      channel.remoteNode._trigger('rtc_answer', desc);
    });
  },

  bind: function(channel) {
    channel.remoteNode.bind('rtc_iceCandidate', function(data) {
      var candidate = new RTCIceCandidate(data);
      channel.pc.addIceCandidate(candidate);
    });

    channel.remoteNode.bind('rtc_answer', function(desc) {
      channel.pc.setRemoteDescription(new RTCSessionDescription(desc));
    });

    channel.remoteNode.bind('rtc_offer', function(desc) {
      channel.pc.setRemoteDescription(new RTCSessionDescription(desc));
      RTCChannelUtils.sendAnswer(channel);
    });
  },

  addStream: function(channel) {
    // add audio and video stream options here
  },

  createDataChannel: function(channel) {
    var label = 'mesh';
    // chrome only supports reliable false atm.
    var options = {
      reliable: false
    };
    var dataChannel;
    try {
      dataChannel = channel.pc.createDataChannel(label, options);
    } catch (error) {
      console.log('seems that DataChannel is NOT actually supported!');
      throw error;
    }

    return RTCChannelUtils.addDataChannel(channel, dataChannel);
  },

  addDataChannel: function(channel, dataChannel) {
    channel.dataChannel = dataChannel;
    dataChannel.onopen = function(e) {
      channel.setState(Channel.STATE.OPEN);
      // console.log('data open', channel.getState(), channel.localNode, channel.remoteNode);
      channel.trigger('open', {
        timestamp: e.timestamp,
        data: ['open', dataChannel]
      });
    };
    dataChannel.onclose = function(e) {
      // console.log('data close');
      channel.trigger('close', {
        timestamp: e.timestamp,
        data: ['close', dataChannel]
      });
    };

    // var netChannel = new NetChannel(dataChannel)
    // channel.netChannel = netChannel;
    // netChannel.onmessage = function(msg) {
    //   var s = ab2str(msg);
    //   data = JSON.parse(s);
    //   console.log('netchannel', msg);
    //   channel.trigger('message', {
    //     timestamp: Date.now(),
    //     data: data
    //   });
    // }
    dataChannel.onmessage = function(e) {
      var data;
      try {
        data = JSON.parse(e.data);
      } catch(e) {
        console.log("Error parsing ", e.data);
      }
      // console.log('data message', e.data);
      channel.trigger('message', {
        timestamp: e.timestamp,
        data: data
      });
    };
    
    return dataChannel;
  },

};

/**
 * RTCChannel
 * @param localNode {Node}
 * @param remoteNode {Node}
 * @constructor
 */
var RTCChannel = function (localNode, remoteNode) {

  Channel.call(this, localNode, remoteNode);

  this.setState(Channel.STATE.CLOSED);
  this.setMinCallState('send', Channel.STATE.OPEN);
  this.setMinCallState('close', Channel.STATE.OPEN);

};

/**
 * Extend Channel
 * @type {Channel}
 */
RTCChannel.prototype = new Channel();

/**
 * Opens channel
 */
RTCChannel.prototype.open = function () {

  if (this.localNode === this.remoteNode) {
    return;
  }

  if (RTCPeerConnection) {
    RTCChannelUtils.bind(this);
    RTCChannelUtils.createPeerConnection(this);
    RTCChannelUtils.addStream(this);
    RTCChannelUtils.createDataChannel(this);
    if (this.remoteNode.initiator) {
      RTCChannelUtils.sendOffer(this);
    }
  }

};

/**
 * Closes channel
 */
RTCChannel.prototype.close = function () {

};

/**
 * Sends message to remoteNode
 * @param message {string}
 */
RTCChannel.prototype.send = function (message) {
  if (this.getState() === Channel.STATE.OPEN) {
    this.dataChannel.send(message);
    // this.netChannel.send(str2ab(message));
    return true;
  }
  return false;
};
