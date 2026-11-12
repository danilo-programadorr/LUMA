"""Local synthetic browser fixture; never contacts Gemini or Google."""
from http.server import HTTPServer,BaseHTTPRequestHandler
import json
from backend.tests.test_research_provider import data,req
from backend.tests.test_research_provider_utf8 import sdk_block
from backend.research.provider import normalize_interaction
from backend.research.display import render_google_display
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        target=self.path.removeprefix('/fixture/');target='' if target in ('default','unterminated') else '_'+target
        d=data();d['steps'][2]['result'][0]['search_suggestions']='<style>.google-fixture{color:green}</style><a class="google-fixture" href="https://www.google.com/search?q=public"'+(' target="'+target+'"' if target else '')+'>ORIGINAL PUBLIC MOCK</a>'
        if self.path.endswith('/unterminated'):d['steps'][2]['result'][0]['search_suggestions']+='<style>'
        d['steps'][-1]['content']=[sdk_block('🚀 A versão estável é pública.','versão estável')]
        r=normalize_interaction(d,req(),'gemini_google_search','gemini-3.8-flash',1,'google_search')
        if r.provider_display_artifact.presentation!='ISOLATED_WINDOW':r=r.model_copy(update={'provider_display_artifact':r.provider_display_artifact.model_copy(update={'presentation':'ISOLATED_WINDOW'})})
        body,headers=render_google_display(r)
        # Simulate a transport-level injected script to test CSP independently.
        body+=b'<script>document.body.dataset.externalXss="executed";</script>'
        out=json.dumps({'body':body.decode(),'headers':headers}).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(out)
if __name__=='__main__':HTTPServer(('127.0.0.1',8788),Handler).serve_forever()
