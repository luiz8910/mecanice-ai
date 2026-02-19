# Mecanice MVP (IA-first + RAG) — FastAPI

## O que isso entrega
- Endpoint: `POST /parts/recommendations`
 Execute também (em ordem):
- RAG: busca trechos em Postgres+pgvector e injeta como `CONTEXT_SOURCES`
- Scripts de ingestão:
 psql "postgresql://postgres:postgres@localhost:5432/mecanice" -f migrations/007_add_workshop_id_to_mechanics.sql
 psql "postgresql://postgres:postgres@localhost:5432/mecanice" -f migrations/008_add_soft_delete_to_mechanics.sql
 psql "postgresql://postgres:postgres@localhost:5432/mecanice" -f migrations/009_create_workshops_and_enforce_mechanic_fk.sql
  - `scripts/ingest_pdf.py`
  - `scripts/ingest_csv.py`

---

## 1) Subir Postgres (exemplo rápido)
Você precisa de um Postgres com pgvector habilitado.

Exemplo (docker):
 ### Exemplo 1: criar workshop
 ```bash
 curl -X POST http://127.0.0.1:8000/workshops \
   -H "Content-Type: application/json" \
   -H "X-Admin-Token: change-me" \
   -d '{
     "name":"Oficina Centro",
     "whatsapp_phone_e164":"+5511999990000",
     "city":"São Paulo",
     "state_uf":"SP",
     "status":"active",
     "notes":"Matriz"
   }'
 ```

 ### Exemplo 2: listar workshops
 ```bash
 curl -X GET "http://127.0.0.1:8000/workshops?limit=50&offset=0" \
   -H "X-Admin-Token: change-me"
 ```

 ### Exemplo 3: atualizar workshop
 ```bash
 curl -X PATCH http://127.0.0.1:8000/workshops/1 \
   -H "Content-Type: application/json" \
   -H "X-Admin-Token: change-me" \
   -d '{
     "name":"Oficina Centro - Unidade 1",
     "status":"active"
   }'
 ```

 ### Exemplo 4: remover workshop
 > A API retorna conflito (`409`) ao tentar remover workshop com mecânicos ativos vinculados.

 ```bash
 curl -X DELETE http://127.0.0.1:8000/workshops/1 \
   -H "X-Admin-Token: change-me"
 ```

 ### Exemplo 5: criar mecânico (workshop_id obrigatório)
docker run --name mecanice-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=mecanice \
  -p 5432:5432 -d postgres:16
```

Depois, execute a migration:
```bash
psql "postgresql://postgres:postgres@localhost:5432/mecanice" -f migrations/001_create_rag_chunks.sql
```
---
     "status":"active",
     "workshop_id":1,

## 2) Configurar .env
Crie um `.env` na raiz. O projeto aceita tanto as variáveis `LLM_*`/`EMBEDDINGS_*`
quanto os aliases legados `OPENAI_*`. As primeiras têm prioridade quando ambas
estão presentes.

Exemplo mínimo (`LLM_*` + `EMBEDDINGS_*`):

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mecanice

LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=SEU_TOKEN
LLM_MODEL=gpt-4.1-mini

# Embeddings (recomendado)
EMBEDDINGS_PROVIDER=openai_compatible
EMBEDDINGS_BASE_URL=https://api.openai.com/v1
EMBEDDINGS_API_KEY=SEU_TOKEN
EMBEDDINGS_MODEL=text-embedding-3-small
```

Se você usa nomes legados do OpenAI, eles também funcionarão como fallback:

```env
# Legacy/OpenAI aliases (opcionais - usados somente se LLM_* não estiverem setadas)
OPENAI_API_KEY=SEU_TOKEN
OPENAI_MODEL_PRIMARY=gpt-4o-mini
OPENAI_MODEL_FALLBACK=gpt-5-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Para desenvolvimento local sem embeddings pagos:
```env
EMBEDDINGS_PROVIDER=dummy
```

---

## 3) Instalar e rodar API
```bash
pip install -r requirements.txt
# Use the prepared module that registers the quotes router and hexagonal wiring:
uvicorn app.app_with_quotes:app --reload --host 0.0.0.0 --port 8000
```

Health check:
```bash
curl http://127.0.0.1:8000/health
```

---

## 4) Ingerir catálogos no RAG
PDF:
```bash
python scripts/ingest_pdf.py --pdf ./seu_catalogo.pdf --source-type catalog
```

CSV/XLSX:
```bash
python scripts/ingest_csv.py --csv ./tabela_aplicacoes.csv --source-type catalog
```

---

## 5) Testar recomendação
```bash
curl -X POST http://127.0.0.1:8000/parts/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "request_id":"req_123",
    "user_text":"Qual pastilha do Vectra 2000?",
    "images_base64":[],
    "known_fields":{"axle":"unknown","rear_brake_type":"unknown","engine":"unknown","abs":"unknown"},
    "context_sources":[]
  }'
```

---

## Observações importantes
- O modelo só deve preencher `part_numbers` quando houver evidência em `CONTEXT_SOURCES`.
- O RAG aqui é simples (top-k). Depois você pode:
  - filtrar por `source_type`,
  - armazenar metadados mais ricos,
  - criar índices por marca/modelo/ano (para acelerar).


## 6) Migration de mecânicos/oficinas
Execute também (em ordem):
```bash
psql "postgresql://postgres:postgres@localhost:5432/mecanice" -f migrations/002_create_mechanics.sql
psql "postgresql://postgres:postgres@localhost:5432/mecanice" -f migrations/007_add_workshop_id_to_mechanics.sql
psql "postgresql://postgres:postgres@localhost:5432/mecanice" -f migrations/008_add_soft_delete_to_mechanics.sql
psql "postgresql://postgres:postgres@localhost:5432/mecanice" -f migrations/009_create_workshops_and_enforce_mechanic_fk.sql
```

### Admin token (MVP)
No `.env`:
```env
ADMIN_TOKEN=change-me
```

### Exemplo 1: criar workshop
```bash
curl -X POST http://127.0.0.1:8000/workshops \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: change-me" \
  -d '{
    "name":"Oficina Centro",
    "whatsapp_phone_e164":"+5511999990000",
    "city":"São Paulo",
    "state_uf":"SP",
    "status":"active",
    "notes":"Matriz"
  }'
```

### Exemplo 2: listar workshops
```bash
curl -X GET "http://127.0.0.1:8000/workshops?limit=50&offset=0" \
  -H "X-Admin-Token: change-me"
```

### Exemplo 3: atualizar workshop
```bash
curl -X PATCH http://127.0.0.1:8000/workshops/1 \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: change-me" \
  -d '{
    "name":"Oficina Centro - Unidade 1",
    "status":"active"
  }'
```

### Exemplo 4: remover workshop
> A API retorna conflito (`409`) ao tentar remover workshop com mecânicos ativos vinculados.

```bash
curl -X DELETE http://127.0.0.1:8000/workshops/1 \
  -H "X-Admin-Token: change-me"
```

### Exemplo 5: criar mecânico (workshop_id obrigatório)
```bash
curl -X POST http://127.0.0.1:8000/mechanics \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: change-me" \
  -d '{
    "name":"Oficina do Zé",
    "whatsapp_phone_e164":"+5511999999999",
    "city":"São Paulo",
    "state_uf":"SP",
    "status":"active",
    "workshop_id":1,
    "categories":["freios"],
    "notes":"tester"
  }'
```

### Exemplo 6: listar mecânicos por workshop
```bash
curl -X GET "http://127.0.0.1:8000/mechanics?workshop_id=1" \
  -H "X-Admin-Token: change-me"
```

---

## Local development (WSL) — Postgres + pgvector (docker-compose) & tests

We include a `docker-compose.yml` and helper scripts to run Postgres with pgvector locally.

1. Copy env sample:

```bash
cp .env.sample .env
```

2. Start Postgres+pgvector with Docker Compose:

```bash
docker compose up -d
```

3. Wait for DB readiness (helper):

```bash
./scripts/wait_for_db.sh
```

4. Install Python deps and run the app (inside WSL):

```bash
python -m pip install -r requirements.txt
uvicorn app.app_with_quotes:app --reload --host 0.0.0.0 --port 8000
```

5. Health check:

```bash
curl http://localhost:8000/health
```

6. Run unit tests (install pytest first):

```bash
python -m pip install pytest
pytest -q
```

Notes:
- The project is being refactored toward a hexagonal-style structure (`domain/` for entities & ports, `app/` for use-cases + routers, and `infrastructure/` for adapters such as Postgres and WhatsApp). At present, most code still resides under `app/`, and some of these directories may not yet exist or may be incomplete. The router module `app.app_with_quotes` wires the current adapters for local development.
- If you prefer the older `app.main:app` entrypoint, it still exists, but the recommended entry is `app.app_with_quotes:app` to include the new quotes router wiring.
