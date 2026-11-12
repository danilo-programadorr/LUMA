/** Only the authenticated ControlPlaneClient response path registers trust.
 * Never persist this registry or accept user/database props as HTML authority. */
interface Artifact {presentation?:'SANDBOXED_FRAME'|'ISOLATED_WINDOW';provider:string;provenance:string;retention:string;search_suggestions_html:string[]}
export interface GoogleDelivery {provider:string;status:string;provider_display_artifact?:Artifact|null}
const trusted = new WeakSet<object>();
export function registerAuthenticatedResearchDelivery(path:string,data:unknown):void {
 if(!/^\/v1\/research\/[a-f0-9]{32}$/.test(path)||!data||typeof data!=='object')return;
 const d=data as {display_status?:string;result?:GoogleDelivery};const r=d.result;const a=r?.provider_display_artifact;
 if(d.display_status==='LIVE'&&r?.provider==='gemini_google_search'&&r.status==='COMPLETED'&&a?.presentation!=='ISOLATED_WINDOW'&&a?.provider==='gemini_google_search'&&a.provenance==='AUTHENTICATED_GOOGLE_PROVIDER'&&a.retention==='TRANSIENT_NON_PERSISTABLE_NON_REUSABLE'&&Array.isArray(a.search_suggestions_html)&&a.search_suggestions_html.length>0&&a.search_suggestions_html.length<=5&&a.search_suggestions_html.every(x=>typeof x==='string'&&x.length>0&&new TextEncoder().encode(x).length<=20000))trusted.add(r);
}
export function googleArtifact(result:object):readonly string[]|undefined {
 if(!trusted.has(result))return undefined;
 return (result as GoogleDelivery).provider_display_artifact?.search_suggestions_html;
}
