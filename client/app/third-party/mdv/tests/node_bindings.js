// Copyright 2013 Google Inc.

// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

suite('Node Bindings', function() {

  var testDiv;

  setup(function() {
    testDiv = document.body.appendChild(document.createElement('div'));
  });

  teardown(function() {
    document.body.removeChild(testDiv);
  });

  function dispatchEvent(type, target) {
    var event = document.createEvent('Event');
    event.initEvent(type, true, false);
    target.dispatchEvent(event);
    Platform.performMicrotaskCheckpoint();
  }

  test('Text', function() {
    var text = document.createTextNode('hi');
    var model = {a: 1};
    text.bind('textContent', model, 'a');
    assert.strictEqual('1', text.data);

    model.a = 2;
    Platform.performMicrotaskCheckpoint();
    assert.strictEqual('2', text.data);

    text.unbind('textContent');
    model.a = 3;
    Platform.performMicrotaskCheckpoint();
    assert.strictEqual('2', text.data);

    // TODO(rafaelw): Throw on binding to unavailable property?
  });

  test('Text (undefined value)', function() {
    var text = document.createTextNode('hi');
    var model = {};
    text.bind('textContent', model, 'a');
    assert.strictEqual(text.data, '');
  });

  test('Element', function() {
    var element = document.createElement('div');
    var model = {a: 1, b: 2};
    element.bind('hidden?', model, 'a');
    element.bind('id', model, 'b');

    assert.isTrue(element.hasAttribute('hidden'));
    assert.strictEqual('', element.getAttribute('hidden'));
    assert.strictEqual('2', element.id);

    model.a = null;
    Platform.performMicrotaskCheckpoint();
    assert.isFalse(element.hasAttribute('hidden'));

    model.a = 'foo';
    model.b = 'x';
    Platform.performMicrotaskCheckpoint();
    assert.isTrue(element.hasAttribute('hidden'));
    assert.strictEqual('', element.getAttribute('hidden'));
    assert.strictEqual('x', element.id);
  });

  test('Element (undefined value)', function() {
    var element = document.createElement('div');
    var model = {};
    element.bind('id', model, 'a');
    assert.strictEqual(element.id, '');
  });

  test('Text Input', function() {
    var input = document.createElement('input');
    var model = {x: 42};
    input.bind('value', model, 'x');
    assert.strictEqual('42', input.value);

    model.x = 'Hi';
    assert.strictEqual('42', input.value);
    Platform.performMicrotaskCheckpoint();
    assert.strictEqual('Hi', input.value);

    input.value = 'changed';
    dispatchEvent('input', input);
    assert.strictEqual('changed', model.x);

    input.unbind('value');

    input.value = 'changed again';
    dispatchEvent('input', input);
    assert.strictEqual('changed', model.x);

    input.bind('value', model, 'x');
    model.x = null;
    Platform.performMicrotaskCheckpoint();
    assert.strictEqual('', input.value);
  });

  test('Radio Input', function() {
    var input = document.createElement('input');
    input.type = 'radio';
    var model = {x: true};
    input.bind('checked', model, 'x');
    assert.isTrue(input.checked);

    model.x = false;
    assert.isTrue(input.checked);
    Platform.performMicrotaskCheckpoint();
    assert.isFalse(input.checked);

    input.checked = true;
    dispatchEvent('change', input);
    assert.isTrue(model.x);

    input.unbind('checked');

    input.checked = false;
    dispatchEvent('change', input);
    assert.isTrue(model.x);
  });

  test('Checkbox Input', function() {
    var input = document.createElement('input');
    testDiv.appendChild(input);
    input.type = 'checkbox';
    var model = {x: true};
    input.bind('checked', model, 'x');
    assert.isTrue(input.checked);

    model.x = false;
    assert.isTrue(input.checked);
    Platform.performMicrotaskCheckpoint();
    assert.isFalse(input.checked);

    input.click();
    assert.isTrue(model.x);
    Platform.performMicrotaskCheckpoint();

    input.click();
    assert.isFalse(model.x);
  });
});
