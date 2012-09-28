console.log('Starting tests.');
// var assert = require('assert');
var page = require('webpage').create();
var url = 'http://localhost:8080/api/js_test.html';

function assertEqual(a,b) {
  return a === b;
}

function testChannel() {
  console.log(window.tailbone);
  // tailbone.bind("test", function(){
  //   console.log("bound callback");
  // });
  // tailbone.trigger("test");
}

function testModel() {
  console.log("test model");
  return false;
}

page.onConsoleMessage = function (msg) {
  console.log('page: ' + msg);
};

page.open(url, function (status) {
    //Page is loaded!
    if (status !== "success") {
      console.log("Could not load url " + url);
    } else {
      page.evalute(testChannel);
    }
    phantom.exit();
});
