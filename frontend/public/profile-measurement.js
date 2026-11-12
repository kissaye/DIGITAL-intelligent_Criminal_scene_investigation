window.createProfileMeasurement = function ({viewer,Potree,status,complete,keyboard=window}) {
  const canvas=viewer.renderer.domElement;
  let state='IDLE',points=[],visual=null,press=null;
  function cleanup(){canvas.removeEventListener('pointerdown',down);canvas.removeEventListener('pointerup',up);canvas.removeEventListener('pointercancel',release);canvas.removeEventListener('dblclick',finish);canvas.removeEventListener('contextmenu',context);keyboard.removeEventListener('keydown',key)}
  function cancel(){cleanup();viewer.removeEventListener('cancel_insertions',cancel);if(visual)viewer.scene.removeProfile(visual);visual=null;points=[];press=null;state='CANCELLED';status('已取消剖面');state='IDLE'}
  function down(e){if(e.button===2){cancel();return}if(e.button===0&&e.isPrimary!==false)press={x:e.clientX,y:e.clientY,id:e.pointerId}}
  function release(){press=null}
  function up(e){
    const start=press;press=null;if(!start||e.button!==0||start.id!==e.pointerId||e.detail>1||Math.hypot(e.clientX-start.x,e.clientY-start.y)>5)return;
    const rect=canvas.getBoundingClientRect();
    const p=Potree.Utils.getMousePointCloudIntersection({x:(e.clientX-rect.left)*canvas.clientWidth/rect.width,y:(e.clientY-rect.top)*canvas.clientHeight/rect.height},viewer.scene.getActiveCamera(),viewer,viewer.scene.pointclouds,{pickClipped:false})?.location;
    if(!p||![p.x,p.y,p.z].every(Number.isFinite)){status('未命中点云，请重新选择');return}
    if(points.length&&points[points.length-1].distanceTo(p)<=1e-6){status('剖面相邻点不能重合');return}
    if(points.length>=50){status('最多50个节点，请按 Enter 完成');return}
    points.push(p.clone());visual.addMarker(p.clone());state=points.length>=2?'READY_TO_FINISH':'COLLECTING';status('已选 '+points.length+' 个节点 · Enter 完成 / Esc 取消');
  }
  function finish(){if(state!=='READY_TO_FINISH'){if(state==='COLLECTING')status('剖面至少需要两个点');return}state='COMPLETED';cleanup();complete({points:points.map(({x,y,z})=>({x,y,z}))})}
  function key(e){if(e.key==='Escape')cancel();else if(e.key==='Enter'){e.preventDefault();finish()}}
  function context(e){e.preventDefault();cancel()}
  function begin(){cancel();viewer.dispatchEvent({type:'cancel_insertions'});visual=new Potree.Profile();visual.setWidth(1);viewer.scene.addProfile(visual);state='COLLECTING';canvas.addEventListener('pointerdown',down);canvas.addEventListener('pointerup',up);canvas.addEventListener('pointercancel',release);canvas.addEventListener('dblclick',finish);canvas.addEventListener('contextmenu',context);keyboard.addEventListener('keydown',key);viewer.addEventListener('cancel_insertions',cancel);status('已选 0 个节点 · Enter 完成 / Esc 取消')}
  return {begin,cancel,get state(){return state},preview(width){if(visual){visual.setWidth(width);state='PREVIEWING'}return visual},saving(){if(['COMPLETED','PREVIEWING'].includes(state))state='SAVING'},saved(){cleanup();viewer.removeEventListener('cancel_insertions',cancel);visual=null;points=[];state='IDLE'},failed(){if(state==='SAVING')state='COMPLETED'}};
};
