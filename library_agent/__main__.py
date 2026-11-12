# Explicit local file import and outbound retrieval. No model or Control Plane authority.
import argparse, json, os, signal, stat, time
from pathlib import Path
from device_agent.identity import Identity
from device_agent.client import ChannelError
from backend.app.errors import Fault
from backend.private_library.extract import MAX_BYTES, parser_environment
from .client import LibraryClient

ROOT = Path(__file__).resolve().parents[1]

def import_document(client, store, project, filename, title=None):
    client.library('check', {'project_id': project})
    try:
        raw_path=str(filename)
        if raw_path.startswith(('\\\\','//')) or '://' in raw_path:
            raise Fault('LIBRARY_LOCAL_FILE_REQUIRED',400)
        path = Path(filename).absolute()
        if os.name=='nt':
            import ctypes
            drive_type=ctypes.windll.kernel32.GetDriveTypeW
            drive_type.argtypes=[ctypes.c_wchar_p];drive_type.restype=ctypes.c_uint
            if drive_type(path.anchor) not in (2,3,5,6):raise Fault('LIBRARY_LOCAL_FILE_REQUIRED',400)
        for part in [*reversed(path.parents),path]:
            if getattr(part.lstat(),'st_file_attributes',0)&0x400:raise Fault('LIBRARY_FILE_LINK_UNSUPPORTED',400)
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or getattr(before, 'st_file_attributes', 0) & 0x400:
            raise Fault('LIBRARY_FILE_LINK_UNSUPPORTED', 400)
        if before.st_size > MAX_BYTES:
            raise Fault('LIBRARY_FILE_TOO_LARGE', 400)
        with path.open('rb') as handle:
            opened = os.fstat(handle.fileno())
            if (opened.st_ino, opened.st_dev) != (before.st_ino, before.st_dev):
                raise Fault('LIBRARY_FILE_CHANGED', 400)
            raw = handle.read(MAX_BYTES + 1)
        meta = store.ingest(project, title or path.name, path.suffix.lower(), raw)
    except OSError:
        raise Fault('LIBRARY_FILE_UNAVAILABLE', 400) from None
    client.library('check', {'project_id': project})
    response = client.library('register', {'source': meta.model_dump()})
    if response.get('source_id') != meta.source_id:
        raise ChannelError('DEVICE_RESPONSE_CORRELATION_INVALID')
    return {'status': 'REGISTERED', 'source_id': meta.source_id, 'pages': meta.page_count, 'chunks': meta.chunk_count}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('import', 'run', 'status'))
    parser.add_argument('--file')
    parser.add_argument('--title')
    parser.add_argument('--project', default='meu-gestor')
    parser.add_argument('--endpoint', default='http://127.0.0.1:8770')
    args = parser.parse_args()
    try:
        forbidden = ('LUMA_GEMINI_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY', 'OPENAI_API_KEY', 'LUMA_DATABASE_URL',
                     'LUMA_PG_TEST_PASSWORD', 'LUMA_PG_ADMIN_PASSWORD', 'DATABASE_URL', 'PGPASSWORD', 'LUMA_OWNER_TOKEN', 'LUMA_TOKEN', 'LUMA_ADMIN_CONFIRM_TOKEN')
        if any(os.environ.get(k) for k in forbidden):
            raise ValueError('LIBRARY_RUNTIME_CREDENTIAL_DENIED_USE_LAUNCHER')
        identity = Identity(ROOT / 'runtime/research-agent/identity.db')
        client = LibraryClient(identity, args.endpoint)
        client.library('check', {'project_id': args.project})
        if args.command == 'status':
            print(json.dumps({'status': 'AUTHORIZED', 'enrolled': bool(identity.binding()[0])}))
            return
        from backend.private_library.store import LibraryStore
        store = LibraryStore(ROOT / 'runtime/private-library' / identity.binding()[0], device_id=identity.binding()[0])
        if args.command == 'import':
            if not args.file:
                raise ValueError('LIBRARY_FILE_REQUIRED')
            print(json.dumps(import_document(client, store, args.project, args.file, args.title)))
            return
        signal.signal(signal.SIGINT, lambda *_: client.stop.set())
        signal.signal(signal.SIGTERM, lambda *_: client.stop.set())
        failures = 0
        try:
            while not client.stop.is_set():
                try:
                    result = client.cycle(store)
                    failures = 0
                    if result.get('status') != 'IDLE':
                        print(json.dumps({'status': result.get('status', 'ACCEPTED')}), flush=True)
                except ChannelError as e:
                    if str(e) in ('DEVICE_REVOKED', 'OWNER_BINDING_INACTIVE', 'DEVICE_OWNER_MISMATCH', 'LIBRARY_CAPABILITY_REQUIRED'):
                        raise
                    failures = min(3, failures + 1)
                client.stop.wait(min(60, 3 * 2 ** failures))
        finally:
            client.transport.close()
    except (ChannelError, Fault, ValueError, RuntimeError) as exc:
        code = exc.code if isinstance(exc, Fault) else str(exc)
        print(code if code and len(code) < 100 and all(c.isupper() or c == '_' for c in code) else 'LIBRARY_LOCAL_FAILURE')
        raise SystemExit(1) from None

if __name__ == '__main__':
    main()
