import importlib,io,sqlite3
import pytest
from backend.app.errors import Fault

def modules():
 try:return importlib.import_module('backend.private_library.store'),importlib.import_module('backend.private_library.extract')
 except ModuleNotFoundError:pytest.fail('Private library local engine not implemented')
def store(tmp_path):return modules()[0].LibraryStore(tmp_path/'library',device_id='a'*32)
def pdf_bytes(blank=False,encrypted=False):
 from pypdf import PdfWriter
 from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
 w=PdfWriter();page=w.add_blank_page(612,792)
 if not blank:
  font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
  page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):w._add_object(font)})})
  content=DecodedStreamObject();content.set_data(b'BT /F1 12 Tf 72 720 Td (Synthetic lunar eclipse) Tj ET');page[NameObject('/Contents')]=w._add_object(content)
 if encrypted:w.encrypt('synthetic-password')
 out=io.BytesIO();w.write(out);return out.getvalue()
@pytest.mark.parametrize('ext',['.txt','.md'])
def test_text_extraction(ext):
 pages=modules()[1].extract_pages('Primeira linha.\nRevogação é imediata.'.encode(),ext);assert pages[0]['page'] is None and 'Revogação' in pages[0]['text']
def test_pdf_page():
 pages=modules()[1].extract_pages(pdf_bytes(),'.pdf');assert pages[0]['page']==1 and 'lunar eclipse' in pages[0]['text']
@pytest.mark.parametrize('raw,ext,code',[(b'abc','.epub','LIBRARY_FORMAT_UNSUPPORTED'),(b'\xff','.txt','LIBRARY_ENCODING_UNSUPPORTED'),(b'','.md','LIBRARY_NO_TEXT'),(b'not pdf','.pdf','LIBRARY_DOCUMENT_INVALID')])
def test_invalid_input(raw,ext,code):
 with pytest.raises(Fault) as e:modules()[1].extract_pages(raw,ext)
 assert e.value.code==code
@pytest.mark.parametrize('kwargs,code',[({'blank':True},'LIBRARY_NO_TEXT'),({'encrypted':True},'LIBRARY_ENCRYPTED_PDF_UNSUPPORTED')])
def test_pdf_unreadable(kwargs,code):
 with pytest.raises(Fault) as e:modules()[1].extract_pages(pdf_bytes(**kwargs),'.pdf')
 assert e.value.code==code
def test_size_bound():
 with pytest.raises(Fault) as e:modules()[1].extract_pages(b'x'*(8*1024*1024+1),'.txt')
 assert e.value.code=='LIBRARY_FILE_TOO_LARGE'
def test_cited_lexical_retrieval(tmp_path):
 s=store(tmp_path);raw='Introdução.\nA revogação suspende o acesso imediatamente.\nConclusão.';m=s.ingest('meu-gestor','Manual','.txt',raw.encode());hits=s.retrieve('meu-gestor','revogacao acesso',[m.source_id])
 assert hits and all(h.source_id==m.source_id and h.source_hash==m.content_hash and h.excerpt in raw and h.line_start>=1 and h.line_end>=h.line_start and h.page is None for h in hits)
def test_scope_empty_and_no_invention(tmp_path):
 s=store(tmp_path);m=s.ingest('meu-gestor','Manual','.txt',b'Cancelamento operacional imediato.')
 assert s.retrieve('meu-gestor','galaxias telescopio',[m.source_id])==[]
 assert s.retrieve('outro-projeto','cancelamento',[m.source_id])==[]
 assert s.retrieve('meu-gestor','cancelamento',[])==[]
@pytest.mark.parametrize('project',['../escape','','a/b'])
def test_invalid_scope(tmp_path,project):
 with pytest.raises(Fault):store(tmp_path).ingest(project,'Manual','.txt',b'Texto sintetico valido.')
def test_dedup_restart_immutable_versions(tmp_path):
 s=store(tmp_path);a=s.ingest('meu-gestor','Fonte','.txt',b'Versao um revogacao.');b=s.ingest('meu-gestor','Novo titulo','.txt',b'Versao um revogacao.');assert a.source_id==b.source_id and a.title==b.title
 s=store(tmp_path);assert s.retrieve('meu-gestor','revogacao',[a.source_id]);c=s.ingest('meu-gestor','Fonte','.txt',b'Versao dois cancelamento.');assert c.source_id!=a.source_id and s.retrieve('meu-gestor','revogacao',[a.source_id])
def test_no_plaintext_at_rest(tmp_path):
 s=store(tmp_path);s.ingest('meu-gestor','TituloPrivadoUnicoZyx','.txt','ConfidencialPalavraUnicaXyZ conteúdo restrito.'.encode())
 for p in (tmp_path/'library').rglob('*'):
  if p.is_file():assert not any(x in p.read_bytes() for x in (b'ConfidencialPalavraUnicaXyZ',b'confidencialpalavraunicaxyz',b'TituloPrivadoUnicoZyx'))
def test_ciphertext_tamper(tmp_path):
 s=store(tmp_path);m=s.ingest('meu-gestor','Fonte','.txt',b'Cancelamento interrompe atividades.')
 with sqlite3.connect(tmp_path/'library'/'index.db') as c:c.execute('UPDATE chunks SET ciphertext=?',(b'tampered',))
 with pytest.raises(Fault) as e:s.retrieve('meu-gestor','cancelamento',[m.source_id])
 assert e.value.code=='LIBRARY_STORAGE_INTEGRITY'
def test_pdf_citation(tmp_path):
 s=store(tmp_path);m=s.ingest('meu-gestor','PDF','.pdf',pdf_bytes());hits=s.retrieve('meu-gestor','lunar',[m.source_id]);assert m.page_count==1 and hits[0].page==1
def test_bounded_results(tmp_path):
 s=store(tmp_path);m=s.ingest('meu-gestor','Longo','.md',('Revogação preserva histórico.\n'*400).encode());hits=s.retrieve('meu-gestor','revogacao historico',[m.source_id]);assert m.chunk_count>5 and len(hits)<=5 and all(len(h.excerpt)<=1000 for h in hits)
def test_scrubbed_parser_env(monkeypatch):
 monkeypatch.setenv('LUMA_GEMINI_API_KEY','synthetic');monkeypatch.setenv('LUMA_DATABASE_URL','synthetic');env=modules()[1].parser_environment();assert not any(k.startswith(('LUMA_','GEMINI_','GOOGLE_','OPENAI_','PG')) for k in env) and 'DATABASE_URL' not in env

def test_text_extraction_preserves_parent_logging():
 import logging
 before=logging.root.manager.disable
 logging.disable(logging.NOTSET)
 try:
  modules()[1].extract_pages(b'Synthetic text.', '.txt')
  assert logging.root.manager.disable==logging.NOTSET
 finally:logging.disable(before)

def test_unsupported_extension_is_rejected_even_for_duplicate_bytes(tmp_path):
 s=store(tmp_path);raw=b'Synthetic existing source.';s.ingest('meu-gestor','Original','.txt',raw)
 with pytest.raises(Fault) as e:s.ingest('meu-gestor','Renamed','.exe',raw)
 assert e.value.code=='LIBRARY_FORMAT_UNSUPPORTED'

@pytest.mark.parametrize('field,value',[('page',7),('line_start',9000),('line_end',9001)])
def test_citation_locator_is_authenticated(tmp_path,field,value):
 s=store(tmp_path);m=s.ingest('meu-gestor','Source','.txt',b'Cancelamento controlado.\nReferencia sintetica.')
 with sqlite3.connect(tmp_path/'library'/'index.db') as c:c.execute('UPDATE chunks SET '+field+'=?',(value,))
 with pytest.raises(Fault) as e:s.retrieve('meu-gestor','cancelamento',[m.source_id])
 assert e.value.code=='LIBRARY_STORAGE_INTEGRITY'

def test_nonempty_legacy_storage_not_silently_reinterpreted(tmp_path):
 s=store(tmp_path);s.ingest('meu-gestor','Source','.txt',b'Cancelamento controlado.')
 with sqlite3.connect(tmp_path/'library'/'index.db') as c:
  if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='storage_format'").fetchone():c.execute('DELETE FROM storage_format')
 with pytest.raises(Fault) as e:store(tmp_path)
 assert e.value.code=='LIBRARY_STORAGE_VERSION_UNSUPPORTED'

def test_missing_master_key_never_replaced_over_existing_documents(tmp_path):
 s=store(tmp_path);s.ingest('meu-gestor','Source','.txt',b'Cancelamento controlado.')
 with sqlite3.connect(tmp_path/'library'/'index.db') as c:c.execute('DELETE FROM security')
 with pytest.raises(Fault) as e:store(tmp_path)
 assert e.value.code=='LIBRARY_STORAGE_INTEGRITY'
