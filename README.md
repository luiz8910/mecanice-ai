# Mecanice MVP (IA-first + RAG) — FastAPI

## O que isso entrega
- Endpoint: `POST /parts/recommendations`
- IA retorna **JSON válido** seguindo o contrato
- RAG: busca trechos em Postgres+pgvector e injeta como `CONTEXT_SOURCES`
- Scripts de ingestão:
  - `scripts/ingest_pdf.py`
  - `scripts/ingest_csv.py`

---

## 1) Subir Postgres (exemplo rápido)
Você precisa de um Postgres com pgvector habilitado.

Exemplo (docker):
```bash
docker run --name mecanice-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=mecanice \
  -p 5432:5432 -d postgres:16
```

Depois, execute a migration:
```bash
psql "postgresql://postgres:postgres@localhost:5432/mecanice" -f migrations/001_create_rag_chunks.sql
```

---

## 2) Configurar .env
Crie um `.env` na raiz:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mecanice

# Embeddings (recomendado)
EMBEDDINGS_PROVIDER=openai_compatible
EMBEDDINGS_BASE_URL=https://api.openai.com/v1
EMBEDDINGS_API_KEY=SEU_TOKEN
EMBEDDINGS_MODEL=text-embedding-3-small

# LLM
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=SEU_TOKEN
LLM_MODEL=gpt-4.1-mini
```

> Para desenvolvimento local sem embeddings pagos:
```env
EMBEDDINGS_PROVIDER=dummy
```

---

## 3) Instalar e rodar API
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
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
Execute também:
```bash
psql "postgresql://postgres:postgres@localhost:5432/mecanice" -f migrations/002_create_mechanics.sql
```

### Admin token (MVP)
No `.env`:
```env
ADMIN_TOKEN=change-me
```

### Teste rápido (criar mecânico)
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
    "categories":["freios"],
    "notes":"tester"
  }'
```
