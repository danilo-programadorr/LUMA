"""Ephemeral isolated document. No Google artifact is stored by this renderer."""
import base64,hashlib,html
from backend.app.errors import Fault
# Only this exact maintenance script may execute. Never permit provider scripts.
EXPIRY_SCRIPT="(()=>{const clear=()=>{document.head.querySelectorAll('style').forEach(x=>x.remove());document.body.replaceChildren(Object.assign(document.createElement('p'),{textContent:'GROUNDED_RESULT_NOT_RETAINED'}));};addEventListener('pagehide',clear);setTimeout(clear,120000);})();"
SCRIPT_HASH=base64.b64encode(hashlib.sha256(EXPIRY_SCRIPT.encode()).digest()).decode()
def render_google_display(result):
    artifact=result.provider_display_artifact
    if result.provider!='gemini_google_search' or result.status!='COMPLETED' or not artifact or artifact.presentation!='ISOLATED_WINDOW':raise Fault('INVALID_GOOGLE_DISPLAY',400)
    from .provider import validate_google_suggestions
    for value in artifact.search_suggestions_html:validate_google_suggestions(value,navigation='window')
    sources={s.source_id:s for s in result.sources};markers={}
    for i,citation in enumerate(result.citations,1):
        source=sources[citation.source_id]
        markers.setdefault(citation.end_index,[]).append('<sup><a href="'+html.escape(source.url,quote=True)+'" target="_blank" rel="noopener noreferrer">['+str(i)+']</a></sup>')
    answer='';offset=0
    for end in sorted(markers):answer+=html.escape(result.answer[offset:end])+''.join(markers[end]);offset=end
    answer+=html.escape(result.answer[offset:])
    links=''.join('<li><a href="'+html.escape(s.url,quote=True)+'" target="_blank" rel="noopener noreferrer">'+html.escape(s.title or s.domain)+'</a></li>' for s in result.sources)
    # Provider snippets remain verbatim. App styling is limited to app elements.
    body='<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pesquisa Google</title><style>body{margin:0;background:#07131e}.luma-answer,.luma-sources{color:#e3edf5;font:16px/1.6 system-ui}.luma-live{max-width:1000px;margin:auto;padding:24px}.luma-answer{white-space:pre-wrap}.luma-answer a,.luma-sources a{color:#49dcec}</style></head><body><script>'+EXPIRY_SCRIPT+'</script><main class="luma-live"><article class="luma-answer">'+answer+'</article><section class="luma-sources" aria-label="Fontes"><ul>'+links+'</ul></section><section aria-label="Google Search Suggestions">'+''.join(artifact.search_suggestions_html)+'</section></main></body></html>'
    headers={'Content-Security-Policy':"sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox; default-src 'none'; script-src 'sha256-"+SCRIPT_HASH+"'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'",'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Frame-Options':'DENY','X-Content-Type-Options':'nosniff','Cross-Origin-Opener-Policy':'same-origin','Permissions-Policy':'microphone=(), camera=(), geolocation=()'}
    return body.encode('utf-8'),headers
