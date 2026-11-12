# Trusted fixed entrypoint. Never prints exceptions, paths or parser diagnostics.
import base64, json, sys, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.private_library.extract import MAX_BYTES, parse_direct
from backend.app.errors import Fault

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    logging.disable(logging.CRITICAL)
    try:
        payload = sys.stdin.buffer.read((MAX_BYTES * 4 // 3) + 8)
        raw = base64.b64decode(payload, validate=True)
        if len(raw) > MAX_BYTES:
            raise ValueError()
        data = {'pages': parse_direct(raw, '.pdf')}
    except Fault as e:
        data = {'error': e.code}
    except Exception:
        data = {'error': 'LIBRARY_DOCUMENT_INVALID'}
    sys.stdout.write(json.dumps(data, ensure_ascii=False))

if __name__ == '__main__':
    main()
