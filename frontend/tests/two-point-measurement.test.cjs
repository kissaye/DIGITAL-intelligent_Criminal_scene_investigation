const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

test('two independent picks, cancellation, restart and invalid points', () => {
  const keyboard = new EventTarget();
  const scope = { window: keyboard };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../public/two-point-measurement.js'), 'utf8'), scope);
  const element = new EventTarget();
  Object.assign(element, { clientWidth: 100, clientHeight: 100, getBoundingClientRect: () => ({ left: 0, top: 0, width: 100, height: 100 }) });
  const viewer = new EventTarget();
  let hit = null;
  const visuals = new Set();
  Object.assign(viewer, {
    renderer: { domElement: element },
    scene: { pointclouds: [], getActiveCamera() {}, addMeasurement(value) { visuals.add(value); }, removeMeasurement(value) { visuals.delete(value); } },
    dispatchEvent(event) { return EventTarget.prototype.dispatchEvent.call(this, new Event(event.type)); },
  });
  const Potree = {
    Utils: { getMousePointCloudIntersection: () => hit && { location: hit } },
    Measure: class { constructor() { this.points = []; } addMarker(value) { this.points.push(value); } },
  };
  const vector = (x, y, z) => ({ x, y, z, clone() { return vector(x,y,z); }, distanceTo(point) { return Math.hypot(x-point.x,y-point.y,z-point.z); } });
  const results = [];
  const messages = [];
  const session = keyboard.createTwoPointMeasurement({ viewer, Potree, status: text => messages.push(text), complete: value => results.push(value), keyboard });
  function event(target, type, values = {}) { const value = new Event(type); Object.assign(value, values); target.dispatchEvent(value); }
  function click(x = 10) { event(element, 'pointerdown', { button: 0, pointerId: 1, clientX: x, clientY: 10 }); event(element, 'pointerup', { button: 0, pointerId: 1, clientX: x, clientY: 10 }); }
  for (let i = 0; i < 3; i++) {
    session.begin();
    assert.equal(session.state, 'WAITING_START');
    hit = null; click(); assert.equal(session.state, 'WAITING_START');
    hit = vector(i, 2, 3); click();
    assert.equal(session.state, 'WAITING_END');
    assert.equal(results.length, i);
    click(); assert.equal(results.length, i);
    hit = vector(i+3, 6, 3); click(30);
    assert.equal(results.length, i+1);
    assert.equal(session.state, 'IDLE');
    click(); assert.equal(results.length, i+1);
    assert.equal(Math.hypot(results[i].endPoint.x-results[i].startPoint.x, results[i].endPoint.y-results[i].startPoint.y), 5);
  }
  session.begin(); hit = vector(1,2,3); click();
  event(keyboard, 'keydown', { key: 'Escape' });
  assert.equal(visuals.size, 3);
  session.begin(); click(); event(element, 'pointerdown', { button: 2 });
  assert.equal(results.length, 3);
  assert.equal(visuals.size, 3);
  session.begin(); click(); session.begin();
  assert.equal(visuals.size, 3);
  hit = vector(2,2,3); click(); hit = vector(5,6,3); click();
  assert.equal(results.length, 4);
  session.begin();
  event(element, 'pointerdown', {button:0,pointerId:1,clientX:0,clientY:0});
  event(element, 'pointerup', {button:0,pointerId:1,clientX:30,clientY:0});
  assert.equal(session.state, 'WAITING_START');
  session.cancel();
  assert.ok(messages.includes('起点和终点不能重合'));
});
