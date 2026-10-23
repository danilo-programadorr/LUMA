# Dependências ADK — 2026-10-22

Baseline c461a8f. Documentação oficial consultada antes da instalação: https://adk.dev/2.0/ , https://adk.dev/graphs/ , https://github.com/google/adk-python e https://pypi.org/pypi/google-adk/json . Release estável 2.12.0, sem extras. BaseLlm oficial em https://raw.githubusercontent.com/google/adk-python/v2.12.0/src/google/adk/models/base_llm.py .

Resolução no ambiente original falhou: ADK requer opentelemetry-api<=1.42.1; FastAPI 0.156.2 requer >=1.44.0. ADK também requer websockets<16, enquanto o backend usa 16.1.1. Nenhum pacote do backend foi alterado. Runtime ADK separado em runtime/adk-venv, lock próprio backend/requirements/adk-lock.txt. Ambos preservam google-genai 2.32.0. O FastAPI transitivo 0.141.1 do runtime não será usado como servidor. Sem optional integrations. Processo ADK sem credenciais, DB ou autoridade; protocolo delimitado para chamadas ao ModelProvider no backend. Resolução não equivale a teste funcional.
