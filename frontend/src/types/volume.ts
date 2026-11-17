import type {Point3D,ViewerState} from './viewer'
export interface VolumePayload {center:Point3D;size:Point3D;rotation:Point3D;title?:string|null;description?:string|null;viewerState?:ViewerState}
export interface VolumeMeasurement extends VolumePayload {id:string;length?:number;width?:number;height?:number;volume?:number}
export function volumePayload(value:VolumePayload):VolumePayload {
  const point=(p:Point3D)=>({x:p.x,y:p.y,z:p.z})
  if (![value.center,value.size,value.rotation].every(p=>p&&[p.x,p.y,p.z].every(Number.isFinite)) || ![value.size.x,value.size.y,value.size.z].every(n=>n>0)) throw new Error('包围盒尺寸必须为有限正数，中心与旋转必须为有效数值')
  return {center:point(value.center),size:point(value.size),rotation:point(value.rotation),title:value.title||'',description:value.description||'',viewerState:value.viewerState||{}}
}
