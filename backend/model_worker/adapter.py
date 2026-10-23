"""Only SDK boundary. No database or control-plane imports."""
import json
from pathlib import Path
import httpx
from google import genai
from google.genai import types,errors
from backend.app.model_contracts import ModelDecision
from backend.app.generation import ModelResult,ModelUsage,usage_alerts
from backend.app.errors import Fault
from backend.app.provider_diagnostics import empty_metadata,enum_value,FINISH,BLOCK,CODES,CATEGORIES,proposal_observation,schema_fields
from pydantic import ValidationError

INSTRUCTION_VERSION='luma-system-2'
SYSTEM_INSTRUCTION=Path(__file__).with_name('system_instruction.txt').read_text(encoding='utf8')

class GeminiAdapter:
    def __init__(self,key,config,client=None):
        self.metadata=empty_metadata()
        self.config=config;self.stage="GeminiAdapter initialization";self.generation_attempted=False;self.safe_error_type="Fault";self.safe_detail="NONE"
        self.client=client or genai.Client(api_key=key,http_options=types.HttpOptions(timeout=int(config['timeout']*1000),
            retry_options=types.HttpRetryOptions(attempts=1),client_args={'trust_env':False},async_client_args={'trust_env':False}))
    def close(self): self.client.close()
    def generate(self,context):
        try:
            self.stage="first generation";self.generation_attempted=True
            response=self.client.models.generate_content(model=self.config['model'],contents=context.model_dump_json(),
                config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type='application/json',response_json_schema=ModelDecision.model_json_schema(),
                    thinking_config=types.ThinkingConfig(thinking_level=self.config['thinking_level']),max_output_tokens=self.config['max_output_tokens'],
                    tools=[],automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)))
            self.stage="response validation"
            raw_usage=response.usage_metadata
            usage=ModelUsage(input_tokens=getattr(raw_usage,'prompt_token_count',None),output_tokens=getattr(raw_usage,'candidates_token_count',None),thought_tokens=getattr(raw_usage,'thoughts_token_count',None))
            self.metadata.update(provider_status=200,response_received=True,usage=usage.model_dump(),usage_alerts=usage_alerts(usage))
            feedback=getattr(response,'prompt_feedback',None)
            block=enum_value(getattr(feedback,'block_reason',None),BLOCK)
            self.metadata.update(block_reason=block,blocked=block not in (None,'BLOCK_REASON_UNSPECIFIED'))
            candidates=response.candidates or []
            ratings=list(getattr(feedback,'safety_ratings',None) or [])
            if candidates:ratings+=list(getattr(candidates[0],'safety_ratings',None) or [])
            self.metadata['safety_categories']=sorted({enum_value(getattr(r,'category',None),CATEGORIES) for r in ratings if getattr(r,'blocked',False)}-{None})
            if not candidates:
                raise Fault('MODEL_SAFETY_REJECTION',503) if self.metadata['blocked'] else Fault('MODEL_INVALID_RESPONSE',503)
            reason=enum_value(candidates[0].finish_reason,FINISH)
            self.metadata['finish_reason']=reason
            if reason in ('SAFETY','BLOCKLIST','PROHIBITED_CONTENT','SPII','RECITATION','JAILBREAK','IMAGE_SAFETY','IMAGE_PROHIBITED_CONTENT','IMAGE_RECITATION'): raise Fault('MODEL_SAFETY_REJECTION',503)
            if reason!='STOP':
                self.safe_detail='MAX_TOKENS' if reason=='MAX_TOKENS' else 'NON_STOP_FINISH'
                raise Fault('MODEL_OUTPUT_TRUNCATED' if reason=='MAX_TOKENS' else 'MODEL_INVALID_RESPONSE',503)
            if getattr(response,'function_calls',None): raise Fault('MODEL_INVALID_RESPONSE',503)
            text=response.text
            if not text or len(text.encode('utf8'))>131072: raise Fault('MODEL_INVALID_RESPONSE',503)
            self.stage="schema validation"
            self.metadata['schema_validation']=False
            try:self.metadata['proposal_observation']=proposal_observation(json.loads(text))
            except ValueError:pass
            decision=ModelDecision.model_validate_json(text)
            self.metadata['proposal_observation']['proposal_schema_valid']=True
            self.metadata['schema_validation']=True
            return ModelResult(decision=decision,model_name=self.config['model'],instruction_version=INSTRUCTION_VERSION,
                usage=usage)
        except Fault: raise
        except httpx.TimeoutException:
            self.metadata['retryable']=True
            raise Fault('MODEL_TIMEOUT',504) from None
        except errors.APIError as exc:
            self.safe_error_type='APIError'
            code=getattr(exc,'code',None)
            status=code if type(code) is int and 100<=code<=599 else None
            self.metadata.update(provider_status=status,provider_code=enum_value(getattr(exc,'status',None),CODES),
                provider_error_type=enum_value(type(exc).__name__,{'ClientError','ServerError','APIError'}),
                retryable=status in (408,429) or bool(status and status>=500),response_received=True)
            self.safe_detail='HTTP_'+str(status) if status in (400,401,403,408,429,500,502,503,504) else 'HTTP_OTHER'
            mapped='MODEL_INVALID_REQUEST' if status==400 else 'MODEL_AUTH_ERROR' if status in (401,403) else 'MODEL_TIMEOUT' if status==408 else 'MODEL_RATE_LIMIT' if status==429 else 'MODEL_UNAVAILABLE' if status and status>=500 else 'MODEL_PROVIDER_ERROR'
            raise Fault(mapped,504 if mapped=='MODEL_TIMEOUT' else 503) from None
        except ValidationError as exc:
            self.safe_error_type='ValidationError'
            if 'proposal_observation' in self.metadata:
                observation=self.metadata['proposal_observation']
                observation['schema_error_fields']=schema_fields(exc.errors(include_input=False,include_context=False,include_url=False))
                observation['proposal_schema_valid']=False if any(x.startswith('proposal.') for x in observation['schema_error_fields']) else None
            self.metadata.update(schema_validation=False,safe_schema_error='INVALID_JSON' if any(e['type']=='json_invalid' for e in exc.errors(include_input=False,include_context=False,include_url=False)) else 'SCHEMA_VALIDATION')
            raise Fault('MODEL_INVALID_RESPONSE',503) from None
        except httpx.HTTPError: raise Fault('MODEL_UNAVAILABLE',503) from None
        except (ValueError,TypeError,AttributeError):
            self.safe_error_type='ValidationError' if self.stage=='schema validation' else 'ValueError'
            raise Fault('MODEL_INVALID_RESPONSE',503) from None
        except Exception:
            self.safe_error_type='InternalError'
            raise Fault('MODEL_ERROR',503) from None
