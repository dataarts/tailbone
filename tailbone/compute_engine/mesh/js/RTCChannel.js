/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/4/13
 * Time: 3:02 AM
 */

// Polyfills
var getUserMedia = (navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia || navigator.msGetUserMedia);
var nativeRTCIceCandidate = (window.mozRTCIceCandidate || window.RTCIceCandidate);
var nativeRTCSessionDescription = (window.mozRTCSessionDescription || window.RTCSessionDescription); // order is very important: "RTCSessionDescription" defined in Nighly but useless
var PeerConnection = (window.PeerConnection || window.webkitPeerConnection00 || window.webkitRTCPeerConnection || window.mozRTCPeerConnection);

var ICE_SERVERS = (function() {
    if (navigator.mozGetUserMedia) {
        return [{url: 'stun:23.21.150.121'}];
    } else {
        return [{url: 'stun:stun.l.google.com:19302'}];
    }
})();
var DATA_CHANNEL_CONFIG = {
    optional: [{RtpDataChannels: true}, 
               {DtlsSrtpKeyAgreement: true}]
};

var DATA_CHANNEL_SUPPORTED = (function() {
    try {
      // raises exception if createDataChannel is not supported
      var pc = new PeerConnection({iceServers: ICE_SERVERS}, 
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

var RTCChannelUtils = {

    preferOpus: function (sdp) {

        var sdpLines = sdp.split('\r\n'),
            mLineIndex;

        for (var i = 0; i < sdpLines.length; i++) {

            if (sdpLines[i].search('m=audio') !== -1) {

                mLineIndex = i;
                break;

            }
        }
        if (mLineIndex === null) {

            return sdp;

        }

        for (var i = 0; i < sdpLines.length; i++) {

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
        var newLine = new Array();
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
        var pc = new PeerConnection({iceServers: ICE_SERVERS}, 
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
        }

    },

    sendOffer: function(channel) {
        channel.pc.createOffer(function (desc) {
            desc.sdp = RTCChannelUtils.preferOpus(desc.sdp);
            channel.pc.setLocalDescription(desc);
            channel.remoteNode._trigger('rtc_offer', desc);
        }, function () {
            console.log('createOffer error');
        });
    },

    sendAnswer: function(channel) {
        channel.pc.createAnswer(function(desc) {
            channel.pc.setLocalDescription(desc);
            channel.remoteNode._trigger('rtc_answer', desc);
        });
    },

    bind: function(channel) {
        channel.remoteNode.bind('rtc_iceCandidate', function(data) {
            var candidate = new nativeRTCIceCandidate(data);
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
        var label = 'datachannel'
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

    if (PeerConnection) {
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
        return true;
    }
    return false;
};
