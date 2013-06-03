/**
 * @author Doug Fritz dougfritz@google.com
 * @author Maciej Zasada maciej@unit9.com
 * @copyright 2013 UNIT9 Ltd.
 * Date: 6/2/13
 * Time: 11:05 PM
 */

var mesh;

function handleOpen() {

    console.log('handle open');

}

function handleEnter(node) {

    console.log('handle enter', node);

}

function handleLeave(node) {

    console.log('handle leave', node);

}

function handleTest(data1, data2) {

    console.log('handle test', data1, data2);

}

function handleError() {

    console.log('handle error');

}

function handleClose() {

    console.log('handle closed');

}

function main() {

    // we can specify global options so all new Mesh instances will derive from it
    Mesh.options.apiUrl = '/api';

    // create new Mesh instance
    mesh = new Mesh();

    // connect to server
    mesh.connect();

    // bind events
    mesh.bind('open', handleOpen);
    mesh.bind('enter', handleEnter);
    mesh.bind('leave', handleLeave);
    mesh.bind('test', handleTest);
    mesh.bind('error', handleError);
    mesh.bind('close', handleClose);

    // trigger custom event
    mesh.trigger('test', 1, 2);

    // unbind custom event
    mesh.unbind('test');

    // trigger a previously unbound event (will not trigger)
    mesh.trigger('test', 3, 4);

}

main();
