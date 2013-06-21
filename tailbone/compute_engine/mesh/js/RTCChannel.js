/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/4/13
 * Time: 3:02 AM
 */

var ICE_SERVERS = [{url: 'stun:stun.l.google.com:19302'}];
var DATA_CHANNEL_CONFIG = {optional: [{RtpDataChannels: true}, {DtlsSrtpKeyAgreement: true}]};

var RTCPeerConnection = window.RTCPeerConnection || window.webkitRTCPeerConnection || window.mozRTCPeerConnection;

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

    getSocket: function (channel, handler) {

        var self = this,
            socket = SocketChannelUtils.socketsByLocalNode[channel.localNode.uid];

        if (!socket) {

            channel.close();
            return;

        }

        if (socket.readyState === 1) {

            handler.call(self, socket);

        } else {

            socket.addEventListener('open', function () {

                handler.call(self, socket);

            });

        }

    },

    signal: function (channel, type, data) {

        var originalArguments = arguments;

        RTCChannelUtils.getSocket(channel, function (socket) {

            var msg = JSON.stringify(Array.prototype.slice.apply(originalArguments).slice(1));
            socket.send(msg);

        });

    }

};

/**
 * RTCChannel
 * @param localNode {Node}
 * @param remoteNode {Node}
 * @constructor
 */
var RTCChannel = function (localNode, remoteNode) {

    Channel.call(this, localNode,  remoteNode);

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

    var self = this;

    if (this.localNode === this.remoteNode) {

        return;

    }

    if (RTCPeerConnection) {

        var peerConnection = new RTCPeerConnection({iceServers: ICE_SERVERS}, DATA_CHANNEL_CONFIG);

        peerConnection.onicecandidate = function (event) {

//            console.log('onIceCandidate', event);

        };

        peerConnection.onconnecting = function (event) {

            console.log('onConnecting', event);

        };

        peerConnection.onopen = function (event) {

            console.log('onOpen', event);

        };

        if (this.localNode.initiator) {

            peerConnection.createOffer(function (sessionDescription) {

                console.log('got session description', sessionDescription);
                sessionDescription.sdp = RTCChannelUtils.preferOpus(sessionDescription.sdp);
                peerConnection.setLocalDescription(sessionDescription);
                RTCChannelUtils.signal(self, 'rtcoffer', sessionDescription);

            }, function () {

                console.log('createOffer error');

            });

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

    return Channel.prototype.send.call(this, message);

};