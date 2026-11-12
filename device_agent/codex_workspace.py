"""Trusted local mapping. The model receives logical IDs, never arbitrary roots."""
import hashlib,json,os,re,stat,tempfile
from pathlib import Path
from backend.codex.contracts import relative_path,WorkspaceManifest

def canonical_json(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def fingerprint(value):return hashlib.sha256(canonical_json(value)).hexdigest()
def reject_links(path):
    """Reject reparse points and hardlinked files, including ancestor junctions."""
    path=Path(path).absolute()
    for node in [*reversed(path.parents),path]:
        st=node.lstat()
        if stat.S_ISLNK(st.st_mode) or getattr(st,'st_file_attributes',0)&0x400:raise ValueError('CODEX_WORKSPACE_ESCAPE')
        if stat.S_ISREG(st.st_mode) and st.st_nlink!=1:raise ValueError('CODEX_WORKSPACE_ESCAPE')
    return path
def checked_file(root,relative,*,exists=True):
    relative_path(relative);root=Path(root)
    candidate=root/relative
    if not candidate.resolve().is_relative_to(root.resolve()):raise ValueError('CODEX_WORKSPACE_ESCAPE')
    reject_links(candidate if candidate.exists() else candidate.parent)
    if exists and not candidate.is_file():raise ValueError('CODEX_PATH_INVALID')
    if candidate.exists() and not candidate.is_file():raise ValueError('CODEX_PATH_INVALID')
    return candidate
class WorkspaceRegistry:
    def __init__(self,state_dir,managed_root):
        self.state_dir=Path(state_dir).resolve();self.root=Path(managed_root).resolve()
        self.state_dir.mkdir(parents=True,exist_ok=True);self.root.mkdir(parents=True,exist_ok=True)
        reject_links(self.state_dir);reject_links(self.root)
        if self.state_dir.is_relative_to(self.root):raise ValueError('CODEX_STATE_INSIDE_WORKSPACE')
    def _key(self,key):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',key):raise ValueError('CODEX_WORKSPACE_UNKNOWN')
        return self.state_dir/(key+'.json')
    def public(self,entry):
        return {k:entry.get(k,field.default) for k,field in WorkspaceManifest.model_fields.items()}
    def save(self,entry):
        path=self._key(entry['workspace_id'])
        fd,temp=tempfile.mkstemp(prefix='registry-',suffix='.tmp',dir=self.state_dir)
        try:
            with os.fdopen(fd,'wb') as out:out.write(canonical_json(entry));out.flush();os.fsync(out.fileno())
            os.replace(temp,path)
        finally:
            if os.path.exists(temp):os.unlink(temp)
    def _fingerprint(self,entry,path):
        st=path.stat()
        return fingerprint(dict(workspace_id=entry['workspace_id'],project_id=entry['project_id'],target_device_id=entry['target_device_id'],mapping_version=entry['mapping_version'],allowed_execution_modes=entry['allowed_execution_modes'],binary_sha256=entry['binary_sha256'],model=entry['model'],canonical_root=os.path.normcase(str(path)),volume=st.st_dev,file_id=st.st_ino))
    def register(self,key,project,device,root,modes,*,mapping_version=1,display_name='Fixture sintético Codex',binary_sha256='0'*64,model=''):
        path=Path(root).absolute();reject_links(path);path=path.resolve(strict=True)
        if not path.is_dir() or path==self.root or not path.is_relative_to(self.root):raise ValueError('CODEX_WORKSPACE_ESCAPE')
        entry=dict(workspace_id=key,project_id=project,target_device_id=device,display_name=display_name,mapping_version=mapping_version,allowed_execution_modes=modes,enabled=True,canonical_root=str(path))
        entry.update(binary_sha256=binary_sha256,model=model,snapshot_hash=fingerprint(snapshot(path)))
        entry['mapping_fingerprint']=self._fingerprint(entry,path)
        WorkspaceManifest.model_validate(self.public(entry))
        old=self._key(key)
        if old.exists():
            previous=json.loads(old.read_text('utf8'))
            if any(previous.get(k)!=v for k,v in entry.items() if k!='snapshot_hash'):raise ValueError('CODEX_MAPPING_CHANGED')
            if previous.get('snapshot_hash')!=entry['snapshot_hash']:self.save(entry)
            return entry
        self.save(entry);return entry
    def refresh_snapshot(self,key):
        entry=json.loads(self._key(key).read_text('utf8'))
        root=self.resolve(key,entry['project_id'],entry['target_device_id'],entry['mapping_fingerprint'],entry['mapping_version'])
        entry['snapshot_hash']=fingerprint(snapshot(root));self.save(entry)
        return self.public(entry)
    def resolve(self,key,project,device,expected,version,*,execution_mode=None,binary_sha256=None,model=None):
        path=self._key(key)
        if not path.is_file():raise ValueError('CODEX_WORKSPACE_UNKNOWN')
        if path.stat().st_size>8192:raise ValueError('CODEX_MAPPING_CHANGED')
        reject_links(path);entry=json.loads(path.read_text('utf8'))
        WorkspaceManifest.model_validate(self.public(entry))
        if not entry['enabled']:raise ValueError('CODEX_WORKSPACE_DISABLED')
        if (entry['project_id'],entry['target_device_id'])!=(project,device):raise ValueError('CODEX_WORKSPACE_SCOPE')
        root=Path(entry['canonical_root']);reject_links(root);root=root.resolve(strict=True)
        if root==self.root or not root.is_relative_to(self.root):raise ValueError('CODEX_WORKSPACE_ESCAPE')
        if entry['mapping_version']!=version or entry['mapping_fingerprint']!=expected or self._fingerprint(entry,root)!=expected:raise ValueError('CODEX_MAPPING_CHANGED')
        if execution_mode is not None and execution_mode not in entry['allowed_execution_modes']:raise ValueError('CODEX_MODE_DENIED')
        if (binary_sha256 is not None and binary_sha256!=entry['binary_sha256']) or (model is not None and model!=entry['model']):raise ValueError('CODEX_BINARY_OR_MODEL_CHANGED')
        return root
def snapshot(root):
    root=Path(root).resolve(strict=True);reject_links(root);out={}
    for parent,dirs,files in os.walk(root,followlinks=False):
        if len(out)>2048:raise ValueError('CODEX_SNAPSHOT_LIMIT')
        for name in dirs:reject_links(Path(parent)/name)
        for name in files:
            if len(out)>=2048:raise ValueError('CODEX_SNAPSHOT_LIMIT')
            path=Path(parent)/name;relative=path.relative_to(root).as_posix()
            relative_path(relative);reject_links(path);st=path.stat()
            if not stat.S_ISREG(st.st_mode) or st.st_size>1048576:raise ValueError('CODEX_SNAPSHOT_LIMIT')
            raw=path.read_bytes();end=path.stat()
            if (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)!=(end.st_dev,end.st_ino,end.st_size,end.st_mtime_ns):raise ValueError('CODEX_SNAPSHOT_RACE')
            out[relative]={'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw)}
    if sum(x['size'] for x in out.values())>4194304:raise ValueError('CODEX_SNAPSHOT_LIMIT')
    return out
def verify_changes(before,after,allowed,max_files,max_bytes,mode):
    created=sorted(after.keys()-before.keys());deleted=sorted(before.keys()-after.keys())
    modified=sorted(k for k in before.keys()&after.keys() if before[k]!=after[k])
    changed=created+deleted+modified
    size=sum(before.get(k,{}).get('size',0)+after.get(k,{}).get('size',0) for k in changed)
    if deleted or (mode=='READ_ONLY' and changed) or not set(changed)<=set(allowed) or len(changed)>max_files or size>max_bytes:raise ValueError('CODEX_SCOPE_EXCEEDED')
    return dict(created_files=created,modified_files=modified,deleted_files=deleted,changed_files_count=len(changed),changed_files=sorted(changed),changed_bytes=size)
def read_context(root,paths,limit=32768):
    selected=[]
    for relative in paths:
        path=checked_file(root,relative)
        if path.stat().st_size>limit:raise ValueError('CODEX_CONTEXT_LIMIT')
        selected.append({'path':relative,'content':path.read_text('utf8')})
        if sum(len(x['content'].encode('utf8')) for x in selected)>limit:raise ValueError('CODEX_CONTEXT_LIMIT')
    return json.dumps(selected,ensure_ascii=False)
