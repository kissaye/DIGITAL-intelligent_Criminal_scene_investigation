const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('profile uses independent picks, two-node completion, cancellation and retry',()=>{
 const keyboard=new EventTarget(),canvas=new EventTarget(),viewer=new EventTarget(),visuals=new Set(),results=[];
 let point;
 const vector=x=>({x,y:0,z:0,clone(){return vector(x)},distanceTo:p=>Math.abs(x-p.x)});
 Object.assign(canvas,{clientWidth:100,clientHeight:100,getBoundingClientRect:()=>({left:0,top:0,width:100,height:100})});
 viewer.renderer={domElement:canvas};viewer.scene={pointclouds:[],getActiveCamera(){},addProfile:p=>visuals.add(p),removeProfile:p=>visuals.delete(p)};
 viewer.dispatchEvent=e=>EventTarget.prototype.dispatchEvent.call(viewer,new Event(e.type));
 const Potree={Profile:class{addMarker(){}setWidth(){}},Utils:{getMousePointCloudIntersection:()=>point&&{location:point}}};
 vm.runInNewContext(fs.readFileSync(__dirname+'/../public/profile-measurement.js','utf8'),{window:keyboard});
 const session=keyboard.createProfileMeasurement({viewer,Potree,status(){},complete:r=>results.push(r),keyboard});
 function event(target,type,data={}){const e=new Event(type);Object.assign(e,data);target.dispatchEvent(e)}
 function click(x,detail=1){point=vector(x);event(canvas,'pointerdown',{button:0,pointerId:1,clientX:x,clientY:0});event(canvas,'pointerup',{button:0,pointerId:1,clientX:x,clientY:0,detail})}
 const enter=()=>event(keyboard,'keydown',{key:'Enter'});
 session.begin();click(1);enter();assert.equal(results.length,0);click(2);assert.equal(session.state,'READY_TO_FINISH');enter();enter();assert.equal(results.length,1);assert.equal(results[0].points.length,2);
 session.preview(2);assert.equal(session.state,'PREVIEWING');session.saving();assert.equal(session.state,'SAVING');session.failed();assert.equal(session.state,'COMPLETED');session.saved();assert.equal(session.state,'IDLE');
 session.begin();click(1);event(keyboard,'keydown',{key:'Escape'});assert.equal(session.state,'IDLE');
 session.begin();click(1);event(canvas,'pointerdown',{button:2});assert.equal(session.state,'IDLE');
 session.begin();click(1);viewer.dispatchEvent({type:'cancel_insertions'});assert.equal(session.state,'IDLE');
 session.begin();click(1);session.begin();for(let i=0;i<51;i++)click(i);enter();assert.equal(results[1].points.length,50);
 session.begin();click(1);event(canvas,'pointerdown',{button:0,pointerId:1,clientX:0,clientY:0});event(canvas,'pointerup',{button:0,pointerId:1,clientX:50,clientY:0});assert.equal(session.state,'COLLECTING');click(2);click(2,2);event(canvas,'dblclick');assert.equal(results[2].points.length,2);
});
