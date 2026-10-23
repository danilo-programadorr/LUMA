"""Action intent is a routing constraint, never execution authorization."""
import re,unicodedata
from enum import StrEnum

class ActionIntent(StrEnum):
    INFORMATIONAL='INFORMATIONAL'
    ACTION_REQUEST='ACTION_REQUEST'
    AMBIGUOUS='AMBIGUOUS'

def classify(message):
    text=''.join(c for c in unicodedata.normalize('NFKD',message.casefold()) if not unicodedata.combining(c))
    # Only the current human message is classified; Knowledge and agent outputs are excluded.
    imperative=r'\b(crie|agende|marque|envie|mande|execute|prepare|cancele|remova|atualize|exclua|adicione|registre|apague|reabra|conclua)\b'
    desire=r'\b(quero|preciso|gostaria de)\s+(?:que voce\s+)?(criar|agendar|enviar|preparar|propor|cancelar|atualizar|remover|executar)\b'
    explicit_proposal=re.search(r'\bproponha\b',text) and re.search(r'\b(acao|criar|agendar|enviar|cancelar|atualizar|remover|executar|reuniao|tarefa|calendar|tasks)\b',text)
    if explicit_proposal or re.search(r'\bgere\s+(?:a|uma)\s+proposta\b',text) or re.search(imperative,text) or re.search(desire,text):return ActionIntent.ACTION_REQUEST
    if re.search(r'\b(faca|resolva|cuide disso|de um jeito)\b',text):return ActionIntent.AMBIGUOUS
    return ActionIntent.INFORMATIONAL
