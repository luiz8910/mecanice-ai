# Mecanice Backend

Backend/API do Mecanice para o fluxo interno de cotação entre mecânicos e lojas de autopeças.

## Produto atual
- O MVP é browser-first.
- Não há integração WhatsApp no fluxo principal.
- O backend sustenta threads de cotação, mensagens internas no navegador, sugestões opcionais de peças e ofertas estruturadas por item solicitado.
- Cada thread pode conter múltiplos `requested_items`, com veículo e oficina no nível da thread.
- Respostas do vendedor passam por `DRAFT`, `SUBMITTED_OPTIONS`, `FINALIZED_QUOTE` e `proposal_sent`; o envio final de orçamento fecha a thread e expõe uma ordem de serviço para o mecânico.

## Stack
- Python 3.11+
- FastAPI (`main.py`)
- PostgreSQL
- SQLAlchemy
- Redis/Celery ainda existem no repositório, mas não fazem parte do fluxo principal desta API MVP

## Principais recursos expostos
- `POST /auth/login`
- `GET /me`
- `POST /threads`
- `GET /threads`
- `GET /threads/{thread_id}`
- `GET/POST /threads/{thread_id}/messages`
- `GET /threads/{thread_id}/request`
- `GET /threads/{thread_id}/suggestions`
- `POST /threads/{thread_id}/offers`
- `GET /threads/{thread_id}/offers`
- `GET /offers/{offer_id}`
- `POST /offers/{offer_id}/items`
- `PUT /offers/{offer_id}/items/{item_id}`
- `DELETE /offers/{offer_id}/items/{item_id}`
- `POST /offers/{offer_id}/submit`
- `POST /offers/{offer_id}/finalize`
- `GET /mechanic/service-orders`
- `GET /mechanic/service-orders/{service_order_id}`
- `GET /threads/{thread_id}/comparison`
- `GET /seller/inbox`

## Estrutura principal
- `main.py`: entrypoint da API
- `src/bot/adapters/driver/fastapi/`: rotas e schemas HTTP
- `src/bot/adapters/driven/db/repositories/`: acesso a dados
- `src/bot/application/services/parts_suggestion_provider.py`: boundary para sugestões opcionais
- `migrations/`: migrations SQL
- `tests/`: testes de API e unidade

## Rodando localmente
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 9000
```

## Documentação
- Swagger UI: `http://127.0.0.1:9000/docs`
- OpenAPI JSON: `http://127.0.0.1:9000/openapi.json`
- Health: `http://127.0.0.1:9000/health`
- Contrato front/back: `docs/FRONTEND_API_CONTRACT.md`

## Testes
```bash
PYTHONPATH=. pytest -q
```

## Observações
- Tabelas legadas de `quotations`, `quotation_items`, `quotation_events` e `quote_conversations` permanecem no banco, mas o fluxo MVP usa `quote_threads`, `part_requests`, `requested_items`, `thread_messages`, `suggested_parts`, `seller_offers` e `seller_offer_items`.
- Sugestões de peças são opcionais e nunca substituem os itens efetivamente ofertados pelo vendedor.
