import json
import logging
from .models import ident, now

logger=logging.getLogger('luma.audit')


def emit(principal_id,project_id,event_type,result,correlation_id,tool_id=None,action_id=None):
    event=dict(event_id=ident(),timestamp=now().isoformat(),principal_id=principal_id,
        project_id=project_id,event_type=event_type,tool_id=tool_id,action_id=action_id,
        result=result,correlation_id=correlation_id)
    logger.info(json.dumps(event))
    return event
