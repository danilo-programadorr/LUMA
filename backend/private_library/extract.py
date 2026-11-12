# Local parsing only. PDF extraction runs in a credential-free subprocess.
import base64, io, json, logging, os, subprocess, sys
from pathlib import Path
from backend.app.errors import Fault

MAX_BYTES = 8 * 1024 * 1024
MAX_CHARS = 2_000_000

def parser_environment():
    return {k: v for k, v in os.environ.items()
            if not k.startswith(('LUMA_', 'OPENAI_', 'GEMINI_', 'GOOGLE_', 'PG', 'AWS_'))
            and k != 'DATABASE_URL' and not k.endswith(('_API_KEY', '_SECRET', '_TOKEN', '_PASSWORD'))}

def extract_pages(raw, extension):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise Fault('LIBRARY_FILE_TOO_LARGE', 400)
    if extension not in ('.pdf', '.txt', '.md'):
        raise Fault('LIBRARY_FORMAT_UNSUPPORTED', 400)
    if extension != '.pdf':
        return parse_direct(raw, extension)
    try:
        result = subprocess.run(
            [sys.executable, '-I', str(Path(__file__).with_name('parser_worker.py'))],
            input=base64.b64encode(raw), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=parser_environment(), timeout=15)
        if result.returncode or len(result.stdout) > 10 * 1024 * 1024:
            raise ValueError()
        data = json.loads(result.stdout)
        code = data.get('error')
        if code in {'LIBRARY_NO_TEXT', 'LIBRARY_ENCRYPTED_PDF_UNSUPPORTED', 'LIBRARY_TEXT_TOO_LARGE', 'LIBRARY_DOCUMENT_INVALID'}:
            raise Fault(code, 400)
        pages = data['pages']
        if not isinstance(pages, list) or not 1 <= len(pages) <= 500:
            raise ValueError()
        if sum(len(p['text']) for p in pages) > MAX_CHARS:
            raise ValueError()
        return pages
    except subprocess.TimeoutExpired:
        raise Fault('LIBRARY_PARSE_TIMEOUT', 400) from None
    except Fault:
        raise
    except Exception:
        raise Fault('LIBRARY_DOCUMENT_INVALID', 400) from None

def parse_direct(raw, extension):
    if extension in ('.txt', '.md'):
        try:
            text = raw.decode('utf-8-sig').replace('\r\n', '\n')
        except UnicodeError:
            raise Fault('LIBRARY_ENCODING_UNSUPPORTED', 400) from None
        pages = [{'page': None, 'text': text}]
    else:
        try:
            if not raw.startswith(b'%PDF-'):
                raise ValueError()
            from pypdf import PdfReader, filters
            if hasattr(filters, 'ZLIB_MAX_OUTPUT_LENGTH'):
                filters.ZLIB_MAX_OUTPUT_LENGTH = MAX_BYTES
            reader = PdfReader(io.BytesIO(raw), strict=True)
            if reader.is_encrypted:
                raise Fault('LIBRARY_ENCRYPTED_PDF_UNSUPPORTED', 400)
            if len(reader.pages) > 500:
                raise Fault('LIBRARY_TEXT_TOO_LARGE', 400)
            pages = []
            total = 0
            for i, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ''
                total += len(text)
                if total > MAX_CHARS:
                    raise Fault('LIBRARY_TEXT_TOO_LARGE', 400)
                pages.append({'page': i, 'text': text})
        except Fault:
            raise
        except Exception:
            raise Fault('LIBRARY_DOCUMENT_INVALID', 400) from None
    if sum(len(p['text']) for p in pages) > MAX_CHARS:
        raise Fault('LIBRARY_TEXT_TOO_LARGE', 400)
    if not any(p['text'].strip() for p in pages):
        raise Fault('LIBRARY_NO_TEXT', 400)
    if any('\x00' in p['text'] for p in pages):
        raise Fault('LIBRARY_DOCUMENT_INVALID', 400)
    return pages
