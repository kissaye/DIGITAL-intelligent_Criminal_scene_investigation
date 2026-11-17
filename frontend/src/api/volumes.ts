import http,{responseData} from './http'
import {volumePayload,type VolumePayload,type VolumeMeasurement} from '@/types/volume'
const mock=import.meta.env.VITE_USE_MOCK!=='false'
const key=(id:string)=>'dici.mock-volumes-'+id
export async function getVolumes(id:string):Promise<VolumeMeasurement[]> {return mock?JSON.parse(localStorage.getItem(key(id))||'[]'):responseData(await http.get('/api/v1/case-versions/'+id+'/volume-measurements'))}
export async function createVolume(id:string,value:VolumePayload):Promise<VolumeMeasurement>{
 const payload=volumePayload(value)
 if(!mock)return responseData(await http.post('/api/v1/case-versions/'+id+'/volume-measurements',payload))
 const item={...payload,id:crypto.randomUUID()};localStorage.setItem(key(id),JSON.stringify([item,...await getVolumes(id)]));return item
}
export async function deleteVolume(versionId:string,id:string){if(!mock){await http.delete('/api/v1/volume-measurements/'+id);return}localStorage.setItem(key(versionId),JSON.stringify((await getVolumes(versionId)).filter(item=>item.id!==id)))}

type ValidationIssue={type?:string;loc?:Array<string|number>;msg?:string;ctx?:Record<string,unknown>}
export function volumeError(error:unknown):string {
 const response=(error as {response?:{status?:number;data?:{message?:unknown;details?:unknown;detail?:unknown}}})?.response
 const data=response?.data
 const detail=data?.details??data?.detail
 if(typeof detail==='string')return detail
 if(Array.isArray(detail)){
  const messages=detail.map((issue:ValidationIssue)=>{
   const path=(issue.loc||[]).filter(value=>value!=='body').join('.')
   const label=path.startsWith('size.')?'包围盒尺寸':path.startsWith('center.')?'中心点坐标':path.startsWith('rotation.')?'旋转角度':path||'包围盒数据'
   if(issue.type==='greater_than')return `${label}必须大于 ${issue.ctx?.gt??0}`
   if(issue.type==='less_than_equal')return `${label}不能超过 ${issue.ctx?.le??'允许上限'}`
   if(issue.type==='finite_number')return `${label}必须是有限数值`
   if(issue.type==='missing')return `${label}为必填项`
   if(issue.type==='extra_forbidden')return `${label}不允许由客户端提交`
   return issue.msg?`${label}格式无效`:`${label}无效`
  }).filter(Boolean)
  if(messages.length)return messages.join('；')
 }
 if(typeof data?.message==='string'&&data.message!=='Request validation failed')return data.message
 if(response?.status===422)return '包围盒数据无效，请检查尺寸、中心点和旋转角度'
 return error instanceof Error&&error.message!=='Request validation failed'?error.message:'包围盒数据无效，请检查尺寸、中心点和旋转角度'
}
