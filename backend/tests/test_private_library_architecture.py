import json,subprocess,sys
from backend.private_library.extract import parser_environment

def test_control_plane_imports_no_private_parser_or_index():
 probe="import json,sys;import backend.private_library.service;print(json.dumps([m for m in ('backend.private_library.store','backend.private_library.extract') if m in sys.modules]))"
 result=subprocess.run([sys.executable,'-c',probe],env=parser_environment(),capture_output=True,text=True,check=True)
 assert json.loads(result.stdout)==[]
