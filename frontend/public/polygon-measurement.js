window.createPolygonMeasurement = function ({viewer, Potree, status, complete, keyboard=window}) {
  const canvas=viewer.renderer.domElement;
  let state='IDLE',points=[],visual=null,press=null;
  function cleanup() {
    canvas.removeEventListener('pointerdown',down);canvas.removeEventListener('pointerup',up);
    canvas.removeEventListener('pointermove',move);canvas.removeEventListener('dblclick',finish);
    canvas.removeEventListener('contextmenu',context);canvas.removeEventListener('pointercancel',release);
    keyboard.removeEventListener('keydown',key);viewer.removeEventListener('cancel_insertions',cancel);
  }
  function cancel() {
    cleanup();if(visual)viewer.scene.removeMeasurement(visual);
    visual=null;points=[];press=null;state='CANCELLED';status('已取消面积测量');state='IDLE';
  }
  function render(preview) {
    if(visual)viewer.scene.removeMeasurement(visual);
    visual=new Potree.Measure();visual.name='区域测量';visual.closed=points.length>=3;
    visual.showDistances=true;visual.showArea=false;
    for(const point of points)visual.addMarker(point.clone());
    if(preview)visual.addMarker(preview.clone());
    viewer.scene.addMeasurement(visual);
  }
  function pick(event) {
    const rect=canvas.getBoundingClientRect();
    return Potree.Utils.getMousePointCloudIntersection({x:(event.clientX-rect.left)*canvas.clientWidth/rect.width,y:(event.clientY-rect.top)*canvas.clientHeight/rect.height},viewer.scene.getActiveCamera(),viewer,viewer.scene.pointclouds,{pickClipped:false})?.location;
  }
  function down(event) { if(event.button===2){cancel();return} if(event.button===0&&event.isPrimary!==false)press={x:event.clientX,y:event.clientY,id:event.pointerId}; }
  function release(){press=null}
  function up(event) {
    const start=press;press=null;
    if(!start||event.button!==0||event.pointerId!==start.id||Math.hypot(event.clientX-start.x,event.clientY-start.y)>5||event.detail>1)return;
    const point=pick(event);
    if(!point||![point.x,point.y,point.z].every(Number.isFinite)){status('未命中点云，请重新选取');return}
    if(points.some(item=>item.distanceTo(point)<=1e-6)){status('请选择不同的顶点');return}
    if(points.length>=100){status('最多选择100个顶点，请按 Enter 完成');return}
    points.push(point.clone());render();state=points.length>=3?'READY_TO_CLOSE':'COLLECTING';
    status('已选 '+points.length+' 点 · Enter 完成 / Esc 取消');
  }
  function move(event){if(press||!points.length)return;const point=pick(event);if(point)render(point)}
  function finish() {
    if(state!=='READY_TO_CLOSE'){status('区域测量至少需要三个点');return}
    state='COMPLETED';cleanup();render();
    complete({points:points.map(({x,y,z})=>({x,y,z}))});
  }
  function context(event){event.preventDefault();cancel()}
  function key(event){if(event.key==='Escape')cancel();else if(event.key==='Enter'){event.preventDefault();finish()}}
  function begin(){
    cancel();viewer.dispatchEvent({type:'cancel_insertions'});state='COLLECTING';
    canvas.addEventListener('pointerdown',down);canvas.addEventListener('pointerup',up);canvas.addEventListener('pointermove',move);
    canvas.addEventListener('dblclick',finish);canvas.addEventListener('contextmenu',context);canvas.addEventListener('pointercancel',release);
    keyboard.addEventListener('keydown',key);viewer.addEventListener('cancel_insertions',cancel);
    status('已选 0 点 · Enter 完成 / Esc 取消');
  }
  return {begin,cancel,get state(){return state},saving(){if(state==='COMPLETED')state='SAVING'},saved(){cleanup();visual=null;points=[];state='IDLE'},failed(){if(state==='SAVING')state='COMPLETED'}};
};
