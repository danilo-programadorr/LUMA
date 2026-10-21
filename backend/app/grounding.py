"""Backend-owned grounding: only whole, unambiguous social turns are exempt.

Unknown text, mixed requests and short factual follow-ups default to REQUIRED.
This policy neither grants capabilities nor interprets model intent as authority.
"""
import re
import unicodedata
from typing import Literal

GroundingRequirement = Literal['NONE', 'REQUIRED']

_SOCIAL = re.compile(
    r'(?:ola|oi|bom dia|boa tarde|boa noite)(?: luma)?'
    r'|(?:muito )?obrigad[oa](?: luma)?'
    r'|(?:tchau|ate logo|ate mais)(?: luma)?'
    r'|(?:ok|entendi|certo)(?: obrigad[oa])?'
    r'|como (?:posso |devo )?(?:conversar|falar) com (?:voce|a luma)'
    r'|como (?:posso )?pedir ajuda (?:a|para a) luma'
)

def grounding_requirement(message: str) -> GroundingRequirement:
    # Normalize accents/case, not content. Never match only a prefix or keyword.
    text=''.join(c for c in unicodedata.normalize('NFD',message.casefold()) if unicodedata.category(c)!='Mn')
    text=re.sub(r'[,!?.;:]', ' ', text)
    text=' '.join(text.split())
    return 'NONE' if _SOCIAL.fullmatch(text) else 'REQUIRED'


def clarification_only(message: str) -> bool:
    # A model boolean alone cannot waive citations on a factual answer.
    return bool(re.fullmatch(
        r'(?:Voce|Você|voce|você)?\s*(?:pode|Pode|poderia|Poderia) '
        r'(?:esclarecer|detalhar|reformular|especificar) '
        r'(?:sua pergunta|a pergunta|o que deseja saber|qual assunto|qual funcionalidade)\?',
        message.strip()))
