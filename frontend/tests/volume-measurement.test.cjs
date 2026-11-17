const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('volume drawing, edit, retry, duplicate guard and cancellation',()=>{
 const keyboard=new EventTarget(),canvas=new EventTarget(),viewer=new EventTarget(),volumes=new Set(),results=[];let box;
 viewer.renderer={domElement:canvas};viewer.scene={removeVolume:v=>volumes.delete(v)};
 viewer.volumeTool={startInsertion(){box=new EventTarget();box.position={x:1,y:2,z:3};box.scale={x:3,y:4,z:5};box.rotation={x:0,y:0,z:0};volumes.add(box);return box}};
 viewer.dispatchEvent=e=>EventTarget.prototype.dispatchEvent.call(viewer,new Event(e.type));
 vm.runInNewContext(fs.readFileSync(__dirname+'/../public/volume-measurement.js','utf8'),{window:keyboard});
 const session=keyboard.createVolumeMeasurement({viewer,status(){},complete:v=>results.push(v),keyboard});
 session.begin();assert.equal(session.state,'DRAWING');box.dispatchEvent(new Event('drop'));assert.equal(session.state,'EDITING');assert.equal(results.length,1);assert.equal(session.saving(),true);assert.equal(session.saving(),false);session.cancel();assert.equal(session.state,'SAVING');session.failed();assert.equal(session.state,'EDITING');session.saving();session.saved();assert.equal(session.state,'IDLE');assert.equal(volumes.size,0);
 for(const action of ['escape','right','tool','cancel']){
 session.begin();if(action==='escape'){const e=new Event('keydown');e.key='Escape';keyboard.dispatchEvent(e)}else if(action==='right')canvas.dispatchEvent(new Event('contextmenu'));else if(action==='tool')viewer.dispatchEvent({type:'cancel_insertions'});else session.cancel();assert.equal(session.state,'IDLE');assert.equal(volumes.size,0)}
 session.begin();box.scale.x=0;box.dispatchEvent(new Event('drop'));assert.equal(results.length,1);assert.equal(session.state,'IDLE');assert.equal(session.saving(),false);
});
