"""Local Owner DB migration with pre/post row-integrity evidence, never credential output."""
import datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.database import engine_for
from sqlalchemy import MetaData,select
from backend.migrate import migrate

def state():
 engine=engine_for(os.environ['LUMA_DATABASE_URL'],'postgresql')
 try:
  with engine.connect() as c:
   m=MetaData();m.reflect(c);tables={};schema=None;devices=[];library=[]
   for name,t in m.tables.items():
    rows=[dict(x) for x in c.execute(select(t)).mappings()]
    if name=='schema_version':schema=rows[0]['version'];continue
    serial=sorted(json.dumps(x,sort_keys=True,separators=(',',':'),default=str) for x in rows)
    tables[name]={'count':len(rows),'sha256':hashlib.sha256('\n'.join(serial).encode()).hexdigest()}
    if name=='device_identities':devices=[{'device_id':x['id'],'status':x['data']['status']} for x in rows]
    if name=='library_devices':library=[{'device_id':x['id'],'enabled':x['data'].get('enabled',False)} for x in rows]
   return {'schema':schema,'tables':tables,'devices':devices,'library':library}
 finally:engine.dispose()

def main():
 before=state()
 if sys.argv[1]=='check':print(json.dumps(before));return
 if before['schema']==9:print(json.dumps({'status':'SCHEMA_ALREADY_CURRENT','schema':9}));return
 if before['schema']!=8:raise ValueError('CODEX_UNEXPECTED_OWNER_SCHEMA')
 directory=ROOT/'runtime/postgresql-backups'
 if not directory.is_dir():raise ValueError('CODEX_EXISTING_BACKUP_DIRECTORY_REQUIRED')
 backup=directory/('before-codex-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.dump')
 env=os.environ.copy();env['PGPASSWORD']=os.environ['LUMA_LOCAL_DB_PASSWORD']
 dump=subprocess.run([str(ROOT/'runtime/postgresql/bin/pg_dump.exe'),'-h','127.0.0.1','-p','55432','-U','luma_test','-d','luma_test_owner_7fb','-Fc','-f',str(backup)],capture_output=True,env=env,timeout=60)
 if dump.returncode:raise ValueError('CODEX_BACKUP_FAILED')
 verify=subprocess.run([str(ROOT/'runtime/postgresql/bin/pg_restore.exe'),'--list',str(backup)],capture_output=True,timeout=20)
 if verify.returncode:raise ValueError('CODEX_BACKUP_INVALID')
 migrate(os.environ['LUMA_DATABASE_URL'],'postgresql',codex=True);after=state()
 unchanged=all(after['tables'].get(n)==value for n,value in before['tables'].items())
 valid=after['schema']==9 and unchanged and after['tables'].get('codex_workspaces',{}).get('count')==0
 report={'status':'PASS' if valid else 'FAILED','before':before,'after':after,'all_existing_rows_unchanged':unchanged,'backup':backup.relative_to(ROOT).as_posix(),'backup_sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),'backup_list_verified':True,'schema_change':'8 -> 9; new empty codex_workspaces only','model_calls':0}
 (ROOT/'reports/FASE_7F_E_OWNER_MIGRATION.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 print(json.dumps({k:report[k] for k in ('status','all_existing_rows_unchanged','backup_list_verified','schema_change','model_calls')}))
 if not valid:raise ValueError('CODEX_OWNER_DATA_INTEGRITY_FAILED')
if __name__=='__main__':
 try:main()
 except Exception as exc:
  code=str(exc);print(json.dumps({'status':'BLOCKED','code':code if code.startswith('CODEX_') and len(code)<80 else 'CODEX_DATABASE_OPERATION_FAILED'}));sys.exit(1)
