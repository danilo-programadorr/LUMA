# Voz desacoplada — decisão arquitetural 2026-10-26

VoiceProvider é somente contrato futuro. Gemini Live é primário para avaliação; OpenAI Realtime/GPT-Live é challenger. Nenhum provider está conectado. Gemini e Google ADK 2.12.0 continuam cérebro/orquestração; não foi criado um décimo agente.

A futura sessão recebe áudio/intenção e produz áudio/eventos de interface. Pedido de ferramenta entra no pipeline LUMA existente. Voz não aprova, não gera ExecutionAuthorization e não substitui HUMAN_OWNER ou Policy Engine. Interrupção/barge-in cancela fala; não equivale a revogação de job. Cancelamento operacional precisa atravessar o Control Plane.

CollaborationPlan prevê execução paralela/sequencial pelos nove agentes existentes, com limites de concorrência e prazo definidos pela orquestração futura. AgentContribution contém mensagens, evidências referenciadas, propostas, objeções ou conclusões; não aceita campos de raciocínio interno nem concessão de autoridade. LUMA/ADK consolida divergências e evidências; nenhuma contribuição autoaprova decisão. Estes contratos não executam agentes adicionais nesta fase.

Antes da fase de voz: rever disponibilidade de modelos e preços oficiais, pedir autorização Owner para custo novo e executar A/B real pt-BR. Medir latência até primeiro áudio p50/p95, naturalidade por avaliação cega, barge-in, estabilidade/reconexão, integração dos agentes e custo por minuto/tarefa. Escolha definitiva somente após evidência. Sem voz real, microfone, SDK de áudio ou chamadas pagas na 7F-D-A.

PrivateLibraryProvider é ponto de extensão futuro, sem ingestão e sem exportar conteúdo privado à web.
