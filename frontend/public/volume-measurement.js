window.createVolumeMeasurement=function({viewer,status,complete,keyboard=window}){
 let state='IDLE',box=null;
 const canvas=viewer.renderer.domElement;
 const serialize=()=>{const xyz=p=>({x:p.x,y:p.y,z:p.z});return {center:xyz(box.position),size:xyz(box.scale),rotation:xyz(box.rotation)}};
 const valid=()=>box&&[box.position,box.scale,box.rotation].every(p=>[p.x,p.y,p.z].every(Number.isFinite))&&[box.scale.x,box.scale.y,box.scale.z].every(n=>n>0);
 function detach(){keyboard.removeEventListener('keydown',key);canvas.removeEventListener('contextmenu',right);viewer.removeEventListener('cancel_insertions',cancel);box?.removeEventListener('drop',drop)}
 function cancel(){if(state==='SAVING')return;detach();if(box)viewer.scene.removeVolume(box);box=null;state='CANCELLED';status('已取消包围盒');state='IDLE'}
 function key(e){if(e.key==='Escape')cancel()}
 function right(e){e.preventDefault();cancel()}
 function drop(){if(state!=='DRAWING')return;if(!valid()){status('包围盒尺寸无效，请重新绘制');cancel();return}state='EDITING';box.removeEventListener('drop',drop);complete(serialize());status('包围盒待服务端计算')}
 function begin(){if(state==='SAVING')return;cancel();viewer.dispatchEvent({type:'cancel_insertions'});state='DRAWING';box=viewer.volumeTool.startInsertion({clip:false,name:'教学包围盒'});box.showVolumeLabel=false;box.addEventListener('drop',drop);keyboard.addEventListener('keydown',key);canvas.addEventListener('contextmenu',right);viewer.addEventListener('cancel_insertions',cancel);status('请在点云中放置包围盒')}
 return {begin,cancel,get state(){return state},saving(){if(state!=='EDITING'||!valid())return false;state='SAVING';return true},failed(){if(state==='SAVING'){state='FAILED';state='EDITING'}},saved(){if(state!=='SAVING')return;detach();if(box)viewer.scene.removeVolume(box);box=null;state='SAVED';state='IDLE'}};
};
