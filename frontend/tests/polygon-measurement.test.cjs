const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
test('polygon collection, completion, cancellation and save retry',()=>{
  const keyboard=new EventTarget(),canvas=new EventTarget(),viewer=new EventTarget();
  Object.assign(canvas,{clientWidth:100,clientHeight:100,getBoundingClientRect:()=>({left:0,top:0,width:100,height:100})});
  let point;const visuals=new Set(),completed=[];
  viewer.renderer={domElement:canvas};
  viewer.scene={pointclouds:[],getActiveCamera(){},addMeasurement:m=>visuals.add(m),removeMeasurement:m=>visuals.delete(m)};
  viewer.dispatchEvent=e=>EventTarget.prototype.dispatchEvent.call(viewer,new Event(e.type));
  const vector=(x,y,z)=>({x,y,z,clone(){return vector(x,y,z)},distanceTo:p=>Math.hypot(x-p.x,y-p.y,z-p.z)});
  const Potree={Utils:{getMousePointCloudIntersection:()=>point&&{location:point}},Measure:class{addMarker(){}}};
  const scope={window:keyboard};vm.runInNewContext(fs.readFileSync(__dirname+'/../public/polygon-measurement.js','utf8'),scope);
  const session=keyboard.createPolygonMeasurement({viewer,Potree,status(){},complete:v=>completed.push(v),keyboard});
  function event(target,type,values={}){const e=new Event(type);Object.assign(e,values);target.dispatchEvent(e)}
  function click(x,y){point=vector(x,y,0);event(canvas,'pointerdown',{button:0,pointerId:1,clientX:x,clientY:y});event(canvas,'pointerup',{button:0,pointerId:1,clientX:x,clientY:y})}
  const enter=()=>event(keyboard,'keydown',{key:'Enter'});
  session.begin();click(0,0);click(3,0);enter();assert.equal(completed.length,0);
  point=vector(3,4,0);event(canvas,'pointerdown',{button:0,pointerId:1,clientX:0,clientY:0});event(canvas,'pointerup',{button:0,pointerId:1,clientX:30,clientY:0});assert.equal(session.state,'COLLECTING');
  click(3,4);assert.equal(session.state,'READY_TO_CLOSE');enter();enter();assert.equal(completed.length,1);assert.equal(completed[0].points.length,3);
  session.saving();assert.equal(session.state,'SAVING');session.failed();assert.equal(session.state,'COMPLETED');session.saving();session.saved();assert.equal(session.state,'IDLE');
  session.begin();click(0,0);event(keyboard,'keydown',{key:'Escape'});assert.equal(session.state,'IDLE');
  session.begin();click(0,0);event(canvas,'pointerdown',{button:2});assert.equal(session.state,'IDLE');
  session.begin();click(0,0);viewer.dispatchEvent({type:'cancel_insertions'});assert.equal(session.state,'IDLE');
  session.begin();click(0,0);session.begin();click(0,0);click(3,0);click(3,4);
  event(canvas,'pointerdown',{button:0,pointerId:1,clientX:3,clientY:4});event(canvas,'pointerup',{button:0,pointerId:1,clientX:3,clientY:4,detail:2});event(canvas,'dblclick');assert.equal(completed.length,2);assert.equal(completed[1].points.length,3);
});
