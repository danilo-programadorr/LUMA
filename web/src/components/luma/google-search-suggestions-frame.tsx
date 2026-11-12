import {googleArtifact} from '@/lib/google-display';
/** The response object must have been admitted by authenticated API transport.
 * Original HTML becomes srcDoc unchanged. No click handler, script, URL rewrite,
 * storage, analytics, same-origin capability or DOM access across this boundary. */
export function GoogleSearchSuggestionsFrame({result}:{result:object}) {
 const artifacts=googleArtifact(result);
 if(!artifacts)return null;
 return <section aria-label="Sugestões oficiais Google">{artifacts.map((html,i)=><iframe key={i} title={'Google Search Suggestions '+(i+1)} srcDoc={html} sandbox="allow-popups allow-popups-to-escape-sandbox" referrerPolicy="no-referrer" className="w-full border-0" style={{height:200}} />)}</section>;
}
