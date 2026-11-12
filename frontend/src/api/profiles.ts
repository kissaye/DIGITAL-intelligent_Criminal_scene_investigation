import http, { responseData } from './http'
import { profilePayload, type ProfilePayload, type ProfileRecord } from '@/types/profile'
const mock=import.meta.env.VITE_USE_MOCK!=='false'
const key=(versionId:string)=>'dici.mock-profiles-'+versionId
export async function getProfiles(versionId:string):Promise<ProfileRecord[]> {
  return mock?JSON.parse(localStorage.getItem(key(versionId))||'[]'):responseData(await http.get('/api/v1/case-versions/'+versionId+'/profiles'))
}
export async function createProfile(versionId:string,value:ProfilePayload):Promise<ProfileRecord> {
  if(!mock)return responseData(await http.post('/api/v1/case-versions/'+versionId+'/profiles',profilePayload(value)))
  const item={...profilePayload(value),id:crypto.randomUUID()}
  localStorage.setItem(key(versionId),JSON.stringify([item,...await getProfiles(versionId)]))
  return item
}
export async function deleteProfile(versionId:string,id:string) {
  if(!mock){await http.delete('/api/v1/profiles/'+id);return}
  localStorage.setItem(key(versionId),JSON.stringify((await getProfiles(versionId)).filter(item=>item.id!==id)))
}
