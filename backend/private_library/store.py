# Rebuildable local index. Content and titles are encrypted; index terms are HMACs.
import hashlib, hmac, json, math, os, re, sqlite3, subprocess, unicodedata
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from backend.app.errors import Fault
from device_agent.identity import protect
from .contracts import SourceMetadata, PrivateExcerpt, PROJECT, ID, source_id
from .extract import extract_pages

STOP = set('como para uma umas uns dos das que qual quais sobre pelo pela com this that the and from for'.split())

def words(text):
    folded = ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')
    return [w for w in re.findall(r'\w+', folded) if len(w) > 2 and w not in STOP]


class LibraryStore:
    def __init__(self, root, *, device_id, protect_key=protect):
        if not re.fullmatch(ID, device_id):
            raise Fault('LIBRARY_DEVICE_INVALID', 400)
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        if os.name == 'nt':
            account = os.environ['USERDOMAIN'] + '\\' + os.environ['USERNAME']
            result = subprocess.run(['icacls', str(self.root), '/inheritance:r', '/grant:r', account + ':(OI)(CI)F', 'SYSTEM:(OI)(CI)F'], capture_output=True)
            if result.returncode:
                raise Fault('LIBRARY_STORAGE_ACL_FAILED', 500)
        self.device_id = device_id
        self.path = self.root / 'index.db'
        with self.connect() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS security(id INTEGER PRIMARY KEY CHECK(id=1), sealed BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS storage_format(id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS documents(source_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, device_id TEXT NOT NULL, content_hash TEXT NOT NULL, metadata BLOB NOT NULL, original BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS chunks(chunk_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, project_id TEXT NOT NULL, page INTEGER, line_start INTEGER NOT NULL, line_end INTEGER NOT NULL, ciphertext BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS postings(project_id TEXT NOT NULL, term BLOB NOT NULL, chunk_id TEXT NOT NULL, frequency INTEGER NOT NULL, PRIMARY KEY(project_id,term,chunk_id));
            """)
            c.execute('BEGIN IMMEDIATE')
            populated=c.execute('SELECT COUNT(*) FROM documents').fetchone()[0] or c.execute('SELECT COUNT(*) FROM chunks').fetchone()[0]
            format_row=c.execute('SELECT version FROM storage_format WHERE id=1').fetchone()
            if format_row is None:
                if populated:raise Fault('LIBRARY_STORAGE_VERSION_UNSUPPORTED',500)
                c.execute('INSERT INTO storage_format VALUES(1,2)')
            elif format_row[0]!=2:raise Fault('LIBRARY_STORAGE_VERSION_UNSUPPORTED',500)
            row = c.execute('SELECT sealed FROM security WHERE id=1').fetchone()
            if row is None and populated:raise Fault('LIBRARY_STORAGE_INTEGRITY',500)
            if row is None:
                sealed = protect_key(os.urandom(32))
                c.execute('INSERT INTO security VALUES (1,?)', (sealed,))
            else:
                sealed = row[0]
            self.key = protect_key(sealed, True)
            if len(self.key) != 32:
                raise Fault('LIBRARY_STORAGE_INTEGRITY', 500)
        self.cipher = AESGCM(self.key)

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.path, timeout=10)
        c.execute('PRAGMA synchronous=FULL')
        try:
            with c:
                yield c
        finally:
            c.close()

    def scope(self, project):
        if not isinstance(project, str) or not re.fullmatch(PROJECT, project):
            raise Fault('LIBRARY_PROJECT_INVALID', 400)

    def aad(self, project, sid, item):
        return json.dumps(['private-library-2', self.device_id, project, sid, item], separators=(',', ':')).encode()

    def encrypt(self, raw, aad):
        nonce = os.urandom(12)
        return nonce + self.cipher.encrypt(nonce, raw, aad)

    def decrypt(self, raw, aad):
        try:
            return self.cipher.decrypt(raw[:12], raw[12:], aad)
        except Exception:
            raise Fault('LIBRARY_STORAGE_INTEGRITY', 500) from None

    def term(self, project, word):
        key = hmac.digest(self.key, ('index\0' + self.device_id + '\0' + project).encode(), 'sha256')
        return hmac.digest(key, word.encode(), 'sha256')

    def metadata(self, row):
        sid, project, did, digest, encoded, _ = row
        if did != self.device_id:
            raise Fault('LIBRARY_STORAGE_INTEGRITY', 500)
        try:
            value = SourceMetadata.model_validate_json(self.decrypt(encoded, self.aad(project, sid, 'metadata')))
            if (value.source_id, value.project_id, value.device_id, value.content_hash) != (sid, project, did, digest):
                raise ValueError()
            return value
        except Fault:
            raise
        except Exception:
            raise Fault('LIBRARY_STORAGE_INTEGRITY', 500) from None

    def ingest(self, project_id, title, extension, raw_bytes):
        self.scope(project_id)
        if extension not in ('.pdf','.txt','.md'):raise Fault('LIBRARY_FORMAT_UNSUPPORTED',400)
        if not isinstance(title, str) or not 1 <= len(title) <= 160 or any(ord(c) < 32 for c in title):
            raise Fault('LIBRARY_SOURCE_INVALID', 400)
        if not isinstance(raw_bytes, bytes) or len(raw_bytes) > 8 * 1024 * 1024:
            raise Fault('LIBRARY_FILE_TOO_LARGE', 400)
        digest = hashlib.sha256(raw_bytes).hexdigest()
        sid = source_id(project_id, self.device_id, digest)
        with self.connect() as c:
            row = c.execute('SELECT * FROM documents WHERE source_id=?', (sid,)).fetchone()
            if row:
                return self.metadata(row)
        pages = extract_pages(raw_bytes, extension)
        chunks = []
        for page in pages:
            text = page['text']
            for start in range(0, len(text), 900):
                end = min(start + 1000, len(text))
                excerpt = text[start:end]
                if excerpt.strip():
                    ordinal = len(chunks)
                    cid = hashlib.sha256((sid + ':' + str(ordinal)).encode()).hexdigest()[:24]
                    chunks.append((cid, page['page'], text[:start].count('\n') + 1, text[:max(start, end - 1)].count('\n') + 1, excerpt))
                if end == len(text):
                    break
        if not 1 <= len(chunks) <= 4000:
            raise Fault('LIBRARY_TEXT_TOO_LARGE', 400)
        meta = SourceMetadata(source_id=sid, project_id=project_id, device_id=self.device_id, title=title, content_hash=digest, extension=extension, byte_count=len(raw_bytes), page_count=sum(p['page'] is not None for p in pages), chunk_count=len(chunks))
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old = c.execute('SELECT * FROM documents WHERE source_id=?', (sid,)).fetchone()
            if old:
                return self.metadata(old)
            if c.execute('SELECT COUNT(*) FROM documents WHERE project_id=?', (project_id,)).fetchone()[0] >= 500:
                raise Fault('LIBRARY_SOURCE_LIMIT', 400)
            c.execute('INSERT INTO documents VALUES (?,?,?,?,?,?)', (sid, project_id, self.device_id, digest, self.encrypt(meta.model_dump_json().encode(), self.aad(project_id, sid, 'metadata')), self.encrypt(raw_bytes, self.aad(project_id, sid, 'original'))))
            for cid, page, first, last, excerpt in chunks:
                c.execute('INSERT INTO chunks VALUES (?,?,?,?,?,?,?)', (cid, sid, project_id, page, first, last, self.encrypt(excerpt.encode(), self.aad(project_id, sid, [cid, page, first, last]))))
                c.executemany('INSERT INTO postings VALUES (?,?,?,?)', [(project_id, self.term(project_id, w), cid, count) for w, count in Counter(words(excerpt)).items()])
        return meta

    def retrieve(self, project_id, query, source_ids):
        self.scope(project_id)
        if not source_ids:
            return []
        if len(source_ids) > 500 or any(not isinstance(s, str) or not re.fullmatch(ID, s) for s in source_ids):
            raise Fault('LIBRARY_SOURCE_INVALID', 400)
        if not isinstance(query, str) or not 1 <= len(query) <= 1200:
            raise Fault('LIBRARY_QUERY_INVALID', 400)
        terms = sorted(set(words(query)))[:32]
        if not terms:
            return []
        scores = defaultdict(float)
        marks = ','.join('?' for _ in source_ids)
        with self.connect() as c:
            count = c.execute('SELECT COUNT(*) FROM chunks WHERE project_id=? AND source_id IN (' + marks + ')', (project_id, *source_ids)).fetchone()[0]
            for w in terms:
                matches = c.execute('SELECT p.chunk_id,p.frequency FROM postings p JOIN chunks c ON c.chunk_id=p.chunk_id WHERE p.project_id=? AND p.term=? AND c.source_id IN (' + marks + ')', (project_id, self.term(project_id, w), *source_ids)).fetchall()
                for cid, frequency in matches:
                    scores[cid] += (1 + math.log((count + 1) / (len(matches) + 1))) * (1 + math.log(frequency))
            result = []
            for cid in sorted(scores, key=lambda cid: (-scores[cid], cid))[:5]:
                chunk = c.execute('SELECT * FROM chunks WHERE chunk_id=? AND project_id=?', (cid, project_id)).fetchone()
                _, sid, _, page, first, last, encoded = chunk
                row = c.execute('SELECT * FROM documents WHERE source_id=? AND project_id=?', (sid, project_id)).fetchone()
                meta = self.metadata(row)
                text = self.decrypt(encoded, self.aad(project_id, sid, [cid, page, first, last])).decode('utf-8')
                result.append(PrivateExcerpt(source_id=sid, source_hash=meta.content_hash, chunk_id=cid, excerpt=text, page=page, line_start=first, line_end=last, score=round(scores[cid], 6)))
            return result

class ScopedLibraryProvider:
    # Implements the reserved two-argument provider with a request-scoped allowlist.
    def __init__(self, store, project_id, source_ids):
        self.store, self.project_id, self.source_ids = store, project_id, tuple(source_ids)
    def retrieve(self, project_id, query):
        if project_id != self.project_id:
            raise Fault('LIBRARY_PROJECT_DENIED', 403)
        return self.store.retrieve(project_id, query, self.source_ids)
