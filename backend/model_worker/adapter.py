"""Only SDK boundary. No database or control-plane imports."""
import json
from pathlib import Path
import httpx
from google import genai
from google.genai import types,errors
from backend.app.model_contracts import ModelDecision
from backend.app.generation import ModelResult,ModelUsage
from backend.app.errors import Fault

INSTRUCTION_VERSION='luma-system-1'
SYSTEM_INSTRUCTION=Path(__file__).with_name('system_instruction.txt').read_text(encoding='utf8')

class GeminiAdapter:
    def __init__(self,key,config,client=None):
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
                    temperature=self.config['temperature'],max_output_tokens=self.config['max_output_tokens'],
                    tools=[],automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)))
            self.stage="response validation"
            candidates=response.candidates or []
            if not candidates:
                raise Fault('MODEL_SAFETY_REJECTION',503) if response.prompt_feedback else Fault('MODEL_INVALID_RESPONSE',503)
            reason=str(candidates[0].finish_reason).split('.')[-1]
            if reason in ('SAFETY','BLOCKLIST','PROHIBITED_CONTENT','SPII','RECITATION'): raise Fault('MODEL_SAFETY_REJECTION',503)
            if reason!='STOP':
                self.safe_detail='MAX_TOKENS' if reason=='MAX_TOKENS' else 'NON_STOP_FINISH'
                raise Fault('MODEL_INVALID_RESPONSE',503)
            if getattr(response,'function_calls',None): raise Fault('MODEL_INVALID_RESPONSE',503)
            text=response.text
            if not text or len(text.encode('utf8'))>131072: raise Fault('MODEL_INVALID_RESPONSE',503)
            self.stage="schema validation"
            decision=ModelDecision.model_validate_json(text)
            usage=response.usage_metadata
            return ModelResult(decision=decision,model_name=self.config['model'],instruction_version=INSTRUCTION_VERSION,
                usage=ModelUsage(input_tokens=getattr(usage,'prompt_token_count',None),output_tokens=getattr(usage,'candidates_token_count',None)))
        except Fault: raise
        except httpx.TimeoutException: raise Fault('MODEL_TIMEOUT',504) from None
        except errors.APIError as exc:
            self.safe_error_type='APIError'
            self.safe_detail='HTTP_'+str(exc.code) if exc.code in (400,401,403,404,429,500,502,503,504) else 'HTTP_OTHER'
            code=getattr(exc,'code',0)
            mapped='MODEL_AUTH_ERROR' if code in (401,403) else 'MODEL_RATE_LIMIT' if code==429 else 'MODEL_UNAVAILABLE' if code in (500,502,503,504) else 'MODEL_ERROR'
            raise Fault(mapped,503) from None
        except httpx.HTTPError: raise Fault('MODEL_UNAVAILABLE',503) from None
        except (ValueError,TypeError,AttributeError):
            self.safe_error_type='ValidationError' if self.stage=='schema validation' else 'ValueError'
            raise Fault('MODEL_INVALID_RESPONSE',503) from None
        except Exception: raise Fault('MODEL_ERROR',503) from None
