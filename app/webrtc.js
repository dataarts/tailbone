var m = new tailbone.Mesh("theroom");
m.bind("msg", function(value) {
  console.log(value);
});


m.trigger("msg", "Hello world");

function addVideo() {
  var ch = m.peers[0]._channels[0];
  var pc = ch.pc;
  window.ch = ch;
  window.pc = pc;
  navigator.webkitGetUserMedia({video: true}, function(stream) {
    window.stream = stream;
    pc.addStream(stream);
    RTCChannelUtils.sendOffer(ch);
  });

  pc.onaddstream = function(e) {
    var video = document.createElement("video");
    document.body.appendChild(video);
    video.src = URL.createObjectURL(e.stream);
  };
}
