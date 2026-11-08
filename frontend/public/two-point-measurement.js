/* Uses Potree picking and Measure rendering, without MeasuringTool insertion markers. */
window.createTwoPointMeasurement = function ({ viewer, Potree, status, complete, keyboard = window }) {
  const element = viewer.renderer.domElement;
  let state = 'IDLE';
  let start = null;
  let press = null;
  let visual = null;

  function cleanup() {
    element.removeEventListener('pointerdown', down);
    element.removeEventListener('pointerup', up);
    element.removeEventListener('pointercancel', release);
    element.removeEventListener('contextmenu', context);
    keyboard.removeEventListener('keydown', key);
    viewer.removeEventListener('cancel_insertions', cancel);
    press = null;
  }
  function cancel() {
    if (state === 'IDLE') return;
    state = 'CANCELLED';
    cleanup();
    if (visual) viewer.scene.removeMeasurement(visual);
    visual = null;
    state = 'IDLE';
    status('已取消测距');
  }
  function release() { press = null; }
  function down(event) {
    if (event.button === 2) { cancel(); return; }
    if (event.button === 0 && event.isPrimary !== false) {
      press = { x: event.clientX, y: event.clientY, id: event.pointerId };
    }
  }
  function up(event) {
    const previous = press;
    press = null;
    if (!previous || event.button !== 0 || previous.id !== event.pointerId) return;
    if (Math.hypot(event.clientX - previous.x, event.clientY - previous.y) > 5) return;
    const rect = element.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const mouse = {
      x: (event.clientX - rect.left) * element.clientWidth / rect.width,
      y: (event.clientY - rect.top) * element.clientHeight / rect.height,
    };
    const hit = Potree.Utils.getMousePointCloudIntersection(
      mouse, viewer.scene.getActiveCamera(), viewer, viewer.scene.pointclouds,
      { pickClipped: false },
    );
    const point = hit?.location;
    if (!point || ![point.x, point.y, point.z].every(Number.isFinite)) {
      status(state === 'WAITING_START' ? '未命中点云，请重新选择起点' : '未命中点云，请重新选择终点');
      return;
    }
    if (state === 'WAITING_START') {
      start = point.clone();
      visual = new Potree.Measure();
      visual.showDistances = true;
      visual.closed = false;
      visual.name = '两点测距';
      visual.addMarker(start.clone());
      viewer.scene.addMeasurement(visual);
      state = 'WAITING_END';
      status('起点已选择，请点击选择终点');
      return;
    }
    if (state !== 'WAITING_END') return;
    if (start.distanceTo(point) <= 0.000001) {
      status('起点和终点不能重合');
      return;
    }
    visual.addMarker(point.clone());
    const result = {
      startPoint: { x: start.x, y: start.y, z: start.z },
      endPoint: { x: point.x, y: point.y, z: point.z },
    };
    state = 'COMPLETED';
    cleanup();
    visual = null;
    state = 'IDLE';
    status('测距已完成');
    complete(result);
  }
  function context(event) { event.preventDefault(); cancel(); }
  function key(event) { if (event.key === 'Escape') cancel(); }
  function begin() {
    cancel();
    viewer.dispatchEvent({ type: 'cancel_insertions' });
    state = 'WAITING_START';
    element.addEventListener('pointerdown', down);
    element.addEventListener('pointerup', up);
    element.addEventListener('pointercancel', release);
    element.addEventListener('contextmenu', context);
    keyboard.addEventListener('keydown', key);
    viewer.addEventListener('cancel_insertions', cancel);
    status('请点击选择起点');
  }
  return { begin, cancel, get state() { return state; } };
};
