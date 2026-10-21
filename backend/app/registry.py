from .models import Project, Tool
from .errors import Fault


AGENTS = tuple({'agent_id':key,'name':name,'status':'PLANNED'} for key,name in (
    ('luma','LUMA — Gestora Geral'),('product','Produto'),('development','Desenvolvimento'),
    ('codex','Codex / Engenheiro de Código'),('qa','QA'),('security','Segurança'),
    ('data','Dados & Analytics'),('growth','Growth & Marketing'),('content','Conteúdo & Social')))


TOOLS = {key:Tool(tool_id=key,status='ENABLED_LOCAL' if key=='knowledge' else 'PLANNED',
    enabled=key=='knowledge',capabilities=tuple(caps.split())) for key,caps in {
    'knowledge':'knowledge.read',
    'google_calendar':'calendar.read calendar.availability calendar.create calendar.update calendar.delete calendar.reminders calendar.invite calendar.write',
    'google_tasks':'tasks.read tasks.create tasks.update tasks.complete tasks.reopen tasks.organize tasks.delete tasks.write',
    'github':'github.read github.write', 'firebase':'firebase.read firebase.deploy',
    'codex':'codex.execute', 'analytics':'analytics.read', 'ads':'ads.manage',
    'pc_runner':'pc.execute'}.items()}


class Projects:
    def __init__(self, endpoint):
        self.items={'meu-gestor':Project(project_id='meu-gestor',name='Meu Gestor',knowledge_endpoint=endpoint,
            metadata={'knowledge_api_version':'0.1.0','brain_version':'0.6.0','engine_version':'1.4.0'})}

    def resolve(self, project_id, principal):
        project=self.items.get(project_id)
        if project is None: raise Fault('UNKNOWN_PROJECT',404)
        if project_id not in principal.project_scopes: raise Fault('FORBIDDEN_SCOPE',403)
        if not project.enabled or project.status!='ACTIVE': raise Fault('PROJECT_SUSPENDED',403)
        return project
