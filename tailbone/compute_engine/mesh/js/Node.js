/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * Date: 6/2/13
 * Time: 11:28 PM
 */

var Node = function (id, socket) {

    this.channels = [
        new SocketChannel(socket),
        new RTCChannel(id)
    ];

};

Node.prototype = new StateDrive();

Node.prototype.trigger = function () {

    var i;

    StateDrive.prototype.trigger.apply(this, arguments);

    /*
    Try sending via the highest channel, upon failure fall back to lower channels
     */
    for (i = this.channels.length - 1; i > -1; --i) {
        if (this.channels[i].send(this, arguments)) {
            return;
        }
    }


};
