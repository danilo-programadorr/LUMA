from threading import RLock
from .errors import Fault
from .models import Session, LearningCandidate, now, ident
from .audit import emit


class LocalState:
    """Bounded ephemeral metadata only; no conversation or canonical write-back."""
    def __init__(self,projects):
        self.projects=projects
        self.sessions={}
        self.candidates={}
        self.lock=RLock()

    def create_session(self,principal,project_id):
        self.projects.resolve(project_id,principal)
        with self.lock:
            if len(self.sessions)>=1000: raise Fault('LOCAL_CAPACITY',503)
            session=Session(principal_id=principal.principal_id,active_project_id=project_id)
            self.sessions[session.session_id]=session
            emit(principal.principal_id,project_id,'SESSION_CREATED','ACTIVE',ident())
            return session

    def session(self,principal,session_id,project_id=None):
        with self.lock:
            session=self.sessions.get(session_id)
            if not session or session.principal_id!=principal.principal_id or session.status!='ACTIVE':
                raise Fault('SESSION_FORBIDDEN',403)
            self.projects.resolve(project_id or session.active_project_id,principal)
            session=session.model_copy(update={'active_project_id':project_id or session.active_project_id,'last_activity':now()})
            self.sessions[session_id]=session
            return session

    def propose_learning(self,principal,candidate:LearningCandidate):
        self.projects.resolve(candidate.project_id,principal)
        if candidate.status!='PROPOSED' or not candidate.evidence: raise Fault('LEARNING_INVALID')
        with self.lock:
            if candidate.candidate_id in self.candidates: raise Fault('LEARNING_EXISTS',409)
            if len(self.candidates)>=1000: raise Fault('LOCAL_CAPACITY',503)
            self.candidates[candidate.candidate_id]=candidate
        emit(principal.principal_id,candidate.project_id,'LEARNING_PROPOSED','PROPOSED',ident())
        return candidate

    def promote(self,*args):
        raise Fault('WRITE_BACK_DISABLED',403)
