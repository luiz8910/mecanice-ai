# Front-End API Contract

Contrato objetivo entre o front-end e o backend browser-first do Mecanice.

## Base
- Base URL local: `http://127.0.0.1:9000`
- Swagger: `http://127.0.0.1:9000/docs`
- Auth: `Authorization: Bearer <token>`
- Formato: JSON
- Estratégia de atualização no MVP: polling

## Atualização do contrato browser-first
- `POST /threads` agora aceita `requested_items[]` e `vehicle` no nível da thread.
- O payload legado com `original_description` + `part_number` + `requested_items_count` continua aceito e é convertido internamente para `requested_items` com 1 item.
- `GET /threads/{thread_id}` e `GET /threads/{thread_id}/comparison` agora devolvem `vehicle`, `workshop`, `requested_items` e ofertas agrupadas por item solicitado.
- Ofertas do vendedor usam os estados `DRAFT`, `SUBMITTED_OPTIONS`, `FINALIZED_QUOTE` e `proposal_sent`.
- Em `SUBMITTED_OPTIONS`, `final_total` e `total_amount` permanecem `null`.
- `POST /offers/{offer_id}/submit` aceita `{"close_quote": true}` para enviar o orçamento final, persistir `proposal_sent` e fechar a thread no mesmo fluxo.
- O mecânico consome ordens de serviço em `GET /mechanic/service-orders` e `GET /mechanic/service-orders/{service_order_id}`.

## Fluxo de autenticação

### `POST /auth/login`
Usado por mecânico, vendedor ou admin.

Request:
```json
{
  "email": "user@example.com",
  "password": "secret123"
}
```

Response:
```json
{
  "token": "jwt",
  "user": {
    "user_id": 11,
    "role": "mechanic",
    "shop_id": 7,
    "vendor_id": null,
    "mechanic_id": 11,
    "name": "Mecanico A",
    "email": "user@example.com"
  }
}
```

### `GET /me`
Usado no bootstrap da aplicação depois do login.

Response:
```json
{
  "user_id": 11,
  "role": "mechanic",
  "shop_id": 7,
  "vendor_id": null,
  "mechanic_id": 11,
  "name": "Mecanico A",
  "email": "user@example.com"
}
```

### `POST /auth/credentials`
Uso administrativo/bootstrap. Não é tela principal do MVP.

Request:
```json
{
  "role": "mechanic",
  "actor_id": 11,
  "email": "mec@example.com",
  "password": "secret123"
}
```

## Fluxo do mecânico

### Tela 1: Lista de threads
Consumir:
- `GET /threads`

Query params:
- `status`
- `limit`
- `offset`

Response resumida:
```json
[
  {
    "id": 1,
    "mechanic_id": 11,
    "workshop_id": 7,
    "status": "open",
    "created_at": "2026-03-10T00:00:00Z",
    "updated_at": "2026-03-10T00:00:00Z",
    "last_message_at": "2026-03-10T00:00:00Z",
    "request_id": 1,
    "original_description": "Preciso de pastilha dianteira",
    "part_number": "PD-123",
    "requested_items_count": 1,
    "vehicle_brand": "Fiat",
    "vehicle_model": "Argo",
    "vehicle_year": "2021",
    "request_status": "ready_for_quote",
    "workshop_name": "Oficina Azul",
    "mechanic_name": "Mecanico A",
    "submitted_offer_count": 1
  }
]
```

### Tela 2: Criar thread
Consumir:
- `POST /threads`

Request:
```json
{
  "original_description": "Preciso de pastilha dianteira",
  "part_number": "PD-123",
  "requested_items_count": 1,
  "vehicle_plate": "BRA2E19",
  "vehicle_brand": "Fiat",
  "vehicle_model": "Argo",
  "vehicle_year": "2021",
  "vehicle_engine": "1.3",
  "vehicle_version": "Drive",
  "vehicle_notes": "Com ABS",
  "generate_suggestions": true
}
```

Response:
```json
{
  "thread": {
    "id": 1,
    "mechanic_id": 11,
    "workshop_id": 7,
    "status": "open",
    "created_at": "2026-03-10T00:00:00Z",
    "updated_at": "2026-03-10T00:00:00Z",
    "last_message_at": "2026-03-10T00:00:00Z"
  },
  "request": {
    "id": 1,
    "thread_id": 1,
    "original_description": "Preciso de pastilha dianteira",
    "requested_items_count": 1,
    "part_number": "PD-123",
    "vehicle_plate": "BRA2E19",
    "vehicle_brand": "Fiat",
    "vehicle_model": "Argo",
    "vehicle_year": "2021",
    "vehicle_engine": "1.3",
    "vehicle_version": "Drive",
    "vehicle_notes": "Com ABS",
    "status": "ready_for_quote",
    "created_at": "2026-03-10T00:00:00Z"
  },
  "messages": [],
  "suggestions": [],
  "offers": []
}
```

Observação:
- se `generate_suggestions=true`, a criação da thread continua mesmo se a sugestão falhar
- o front não deve bloquear a UX esperando sugestões

### Tela 3: Detalhe da thread do mecânico
Consumir:
- `GET /threads/{thread_id}`
- `GET /threads/{thread_id}/messages`
- `GET /threads/{thread_id}/suggestions`
- `GET /threads/{thread_id}/offers`

Também pode usar só `GET /threads/{thread_id}` para hidratação inicial.

Message response:
```json
[
  {
    "id": 1,
    "thread_id": 1,
    "sender_role": "mechanic",
    "sender_user_ref": "mechanic:11",
    "type": "text",
    "body": "Pode ser Cobreq ou TRW",
    "metadata_json": {},
    "created_at": "2026-03-10T00:00:00Z"
  }
]
```

Enviar mensagem:
- `POST /threads/{thread_id}/messages`

Request:
```json
{
  "type": "text",
  "body": "Pode ser Cobreq ou TRW"
}
```

Tipos aceitos:
- `text`
- `system`
- `request_summary`
- `offer_notice`

### Tela 4: Comparação de ofertas
Consumir:
- `GET /threads/{thread_id}/comparison`

Response:
```json
{
  "thread_id": 1,
  "request": {
    "id": 1,
    "thread_id": 1,
    "original_description": "Preciso de pastilha dianteira",
    "requested_items_count": 1,
    "part_number": "PD-123",
    "vehicle_plate": "BRA2E19",
    "vehicle_brand": "Fiat",
    "vehicle_model": "Argo",
    "vehicle_year": "2021",
    "vehicle_engine": "1.3",
    "vehicle_version": "Drive",
    "vehicle_notes": "Com ABS",
    "status": "ready_for_quote",
    "created_at": "2026-03-10T00:00:00Z"
  },
  "offers": [
    {
      "offer_id": 3,
      "seller_id": 21,
      "seller_name": "Loja Azul",
      "seller_shop_id": 9,
      "seller_shop_name": "Autopecas Azul",
      "status": "submitted",
      "total_amount": 191.0,
      "submitted_at": "2026-03-10T00:00:00Z",
      "items": [],
      "notes": null
    }
  ]
}
```

## Fluxo do vendedor

### Tela 1: Inbox do vendedor
Consumir:
- `GET /seller/inbox`

Query params:
- `status`
- `q`
- `page`
- `page_size`

Response:
```json
{
  "items": [
    {
      "inbox_item_id": "1",
      "request_id": "1",
      "store_id": "9",
      "vendor_id": "21",
      "status": "open",
      "created_at": "2026-03-10T00:00:00Z",
      "last_updated_at": "2026-03-10T00:00:00Z",
      "workshop_name": "Oficina Azul",
      "part_number": "PD-123",
      "part_description": "Preciso de pastilha dianteira",
      "vehicle_summary": "Fiat / Argo / 2021",
      "has_offer": false
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

### Tela 2: Detalhe da inbox / builder de oferta
Consumir:
- `GET /seller/inbox/{inbox_item_id}`

Response:
```json
{
  "inbox_item_id": "1",
  "request_id": "1",
  "store_id": "9",
  "vendor_id": "21",
  "status": "open",
  "created_at": "2026-03-10T00:00:00Z",
  "last_updated_at": "2026-03-10T00:00:00Z",
  "workshop": {
    "workshop_id": 7,
    "name": "Oficina Azul",
    "phone": null,
    "address": null
  },
  "part_number": "PD-123",
  "part_description": "Preciso de pastilha dianteira",
  "vehicle_summary": "Fiat / Argo / 2021",
  "original_message": "Preciso de pastilha dianteira",
  "notes": null,
  "messages": [],
  "suggestions": [],
  "current_offer": null
}
```

Atualizar status visual da thread para o vendedor:
- `PATCH /seller/inbox/{inbox_item_id}`

Request:
```json
{
  "status": "awaiting_seller_response"
}
```

### Tela 3: Criar/abrir draft da oferta
Consumir:
- `POST /threads/{thread_id}/offers`

Response:
```json
{
  "id": 3,
  "thread_id": 1,
  "seller_id": 21,
  "seller_shop_id": 9,
  "status": "draft",
  "notes": null,
  "total_amount": null,
  "created_at": "2026-03-10T00:00:00Z",
  "updated_at": "2026-03-10T00:00:00Z",
  "submitted_at": null,
  "seller_name": "Loja Azul",
  "seller_shop_name": "Autopecas Azul",
  "items": []
}
```

### Tela 4: Adicionar item manual
Consumir:
- `POST /offers/{offer_id}/items`

Request:
```json
{
  "source_type": "manual",
  "title": "Pastilha dianteira TRW",
  "brand": "TRW",
  "part_number": "TRW-889",
  "quantity": 2,
  "unit_price": 95.5,
  "compatibility_note": "Compatível com Argo 1.3"
}
```

### Tela 5: Adicionar item a partir de sugestão
Consumir:
- `POST /offers/{offer_id}/items`

Request:
```json
{
  "source_type": "suggested",
  "suggested_part_id": 15,
  "quantity": 2,
  "unit_price": 95.5,
  "compatibility_note": "Tem em estoque"
}
```

Observação:
- o backend faz snapshot dos dados da sugestão no item da oferta
- o front pode enviar `title`, `brand` e `part_number` manualmente, mas não precisa

### Tela 6: Editar item
Consumir:
- `PUT /offers/{offer_id}/items/{item_id}`

Request:
```json
{
  "quantity": 3,
  "unit_price": 94.0,
  "compatibility_note": "Preço atualizado"
}
```

### Tela 7: Remover item
Consumir:
- `DELETE /offers/{offer_id}/items/{item_id}`

Response:
- `204 No Content`

### Tela 8: Submeter oferta
Consumir:
- `POST /offers/{offer_id}/submit`

Response:
```json
{
  "id": 3,
  "thread_id": 1,
  "seller_id": 21,
  "seller_shop_id": 9,
  "status": "submitted",
  "notes": null,
  "total_amount": 191.0,
  "created_at": "2026-03-10T00:00:00Z",
  "updated_at": "2026-03-10T00:00:00Z",
  "submitted_at": "2026-03-10T00:00:00Z",
  "seller_name": "Loja Azul",
  "seller_shop_name": "Autopecas Azul",
  "items": [
    {
      "id": 8,
      "offer_id": 3,
      "source_type": "suggested",
      "suggested_part_id": 15,
      "title": "Pastilha de freio dianteira",
      "brand": "Cobreq",
      "part_number": "PD-123",
      "quantity": 2,
      "unit_price": 95.5,
      "compatibility_note": "Tem em estoque",
      "created_at": "2026-03-10T00:00:00Z"
    }
  ]
}
```

Validações importantes:
- a oferta precisa ter pelo menos 1 item
- `quantity > 0`
- `unit_price > 0` no submit

## Ordem recomendada de consumo por tela

### App bootstrap
1. `POST /auth/login`
2. salvar token
3. `GET /me`
4. decidir shell do app pelo `role`

### Jornada do mecânico
1. `GET /threads`
2. `POST /threads`
3. `GET /threads/{thread_id}`
4. polling em `GET /threads/{thread_id}/messages`
5. polling em `GET /threads/{thread_id}/offers`
6. `GET /threads/{thread_id}/comparison` na tela de comparação

### Jornada do vendedor
1. `GET /seller/inbox`
2. `GET /seller/inbox/{inbox_item_id}`
3. `POST /threads/{thread_id}/offers`
4. `POST /offers/{offer_id}/items`
5. `PUT /offers/{offer_id}/items/{item_id}` conforme edição
6. `POST /offers/{offer_id}/submit`
7. polling em `GET /seller/inbox`

## Polling sugerido
- lista de inbox do vendedor: a cada 10s
- detalhe da thread aberta: a cada 5s
- comparação do mecânico: a cada 10s

## Erros esperados
- `401`: token ausente, inválido ou acesso fora do papel do usuário
- `404`: thread, request, offer ou item inexistente
- `409`: conflitos de credencial
- `422`: validação de payload ou regra de negócio

Formato:
```json
{
  "detail": "mensagem de erro"
}
```

## O que o front precisa assumir hoje
- `POST /auth/credentials` é rota de suporte/admin, não fluxo normal de usuário final
- `/seller/inbox` é a lista principal do vendedor
- `/threads` é a lista principal do mecânico
- sugestões podem vir vazias mesmo com `generate_suggestions=true`
- a UI não deve depender de tempo real por socket

---

## Catálogo de veículos e montadoras

Usado principalmente no formulário de criação de thread pelo mecânico (seleção de veículo).
Os endpoints `GET` **não exigem autenticação**. Mutações (`POST`, `PATCH`, `DELETE`) exigem `X-Admin-Token`.

---

### `GET /manufacturers`

Lista todas as montadoras ativas.

Query params:

| Param | Tipo | Descrição |
|---|---|---|
| `search` | string | Busca parcial no nome (ex: `volk`) |
| `country_of_origin` | string | Filtro exato por país (ex: `Japan`) |
| `limit` | int (default 100) | Paginação |
| `offset` | int (default 0) | Paginação |

Response `200`:
```json
[
  {
    "id": 1,
    "name": "Volkswagen",
    "country_of_origin": "Germany",
    "created_at": "2026-03-28T00:00:00Z",
    "updated_at": "2026-03-28T00:00:00Z"
  },
  {
    "id": 2,
    "name": "Fiat",
    "country_of_origin": "Italy",
    "created_at": "2026-03-28T00:00:00Z",
    "updated_at": "2026-03-28T00:00:00Z"
  }
]
```

---

### `GET /manufacturers/{manufacturer_id}`

Detalhe de uma montadora.

Response `200`:
```json
{
  "id": 1,
  "name": "Volkswagen",
  "country_of_origin": "Germany",
  "created_at": "2026-03-28T00:00:00Z",
  "updated_at": "2026-03-28T00:00:00Z"
}
```

---

### `POST /manufacturers` (admin)

Header obrigatório: `X-Admin-Token: <token>`

Request:
```json
{
  "name": "Toyota",
  "country_of_origin": "Japan"
}
```

Response `201`: mesmo shape do GET detalhe.

Erros:
- `409` — nome já existe

---

### `PATCH /manufacturers/{manufacturer_id}` (admin)

Campos opcionais (envia apenas o que mudar):
```json
{
  "name": "Toyota Brasil",
  "country_of_origin": "Japan"
}
```

Response `200`: mesmo shape do GET detalhe.

---

### `DELETE /manufacturers/{manufacturer_id}` (admin)

Response `204 No Content`.

---

### `GET /vehicles`

Lista veículos com JOIN na montadora. Todos os filtros são opcionais e combináveis.

Query params:

| Param | Tipo | Descrição |
|---|---|---|
| `search` | string | Busca parcial no **modelo** ou **nome da montadora** (ex: `gol`, `fiat`) |
| `manufacturer_id` | int | Todos os veículos de uma montadora |
| `body_type` | string | `hatchback` \| `sedan` \| `pickup` \| `suv` \| `minivan` \| `coupe` \| `van` \| `wagon` \| `convertible` |
| `fuel_type` | string | `flex` \| `gasoline` \| `diesel` \| `hybrid` \| `electric` \| `cng` |
| `country_of_origin` | string | Filtrar pelo país da montadora (ex: `Japan`) |
| `year` | int | Modelos **em produção em** determinado ano (ex: `2015`) |
| `year_from` | int | Ano de início de produção mínimo (ex: `2010`) |
| `year_to` | int | Ano de início de produção máximo (ex: `2020`) |
| `is_current` | bool | `true` = apenas em produção hoje; `false` = apenas descontinuados |
| `engine` | string | Busca parcial no motor (ex: `1.0`, `turbo`, `2.0 TSI`) |
| `limit` | int (default 100) | Paginação |
| `offset` | int (default 0) | Paginação |

Response `200`:
```json
[
  {
    "id": 1,
    "manufacturer_id": 1,
    "manufacturer_name": "Volkswagen",
    "country_of_origin": "Germany",
    "model": "Gol",
    "model_year_start": 2008,
    "model_year_end": 2022,
    "body_type": "hatchback",
    "fuel_type": "flex",
    "engine_displacement": "1.0",
    "created_at": "2026-03-28T00:00:00Z",
    "updated_at": "2026-03-28T00:00:00Z"
  },
  {
    "id": 14,
    "manufacturer_id": 1,
    "manufacturer_name": "Volkswagen",
    "country_of_origin": "Germany",
    "model": "T-Cross",
    "model_year_start": 2019,
    "model_year_end": null,
    "body_type": "suv",
    "fuel_type": "flex",
    "engine_displacement": "1.0 TSI",
    "created_at": "2026-03-28T00:00:00Z",
    "updated_at": "2026-03-28T00:00:00Z"
  }
]
```

Nota: `model_year_end: null` indica modelo ainda em produção.

---

### `GET /vehicles/{vehicle_id}`

Detalhe de um veículo.

Response `200`: mesmo shape do item do array acima.

---

### `POST /vehicles` (admin)

Header obrigatório: `X-Admin-Token: <token>`

Request:
```json
{
  "manufacturer_id": 1,
  "model": "Polo Track",
  "model_year_start": 2023,
  "model_year_end": null,
  "body_type": "hatchback",
  "fuel_type": "flex",
  "engine_displacement": "1.0 MPI"
}
```

Campos obrigatórios: `manufacturer_id`, `model`, `model_year_start`, `body_type`.
`fuel_type` padrão: `"flex"`.

Response `201`: shape completo com `manufacturer_name` e `country_of_origin`.

Erros:
- `404` — `manufacturer_id` não existe

---

### `PATCH /vehicles/{vehicle_id}` (admin)

Todos os campos opcionais:
```json
{
  "model_year_end": 2025,
  "engine_displacement": "1.0 TSI"
}
```

Response `200`: shape completo.

---

### `DELETE /vehicles/{vehicle_id}` (admin)

Response `204 No Content`.

---

### Padrão de erros (veículos e montadoras)

| Código | Quando |
|---|---|
| `404` | ID não encontrado ou soft-deleted |
| `409` | Nome de montadora duplicado |
| `422` | Payload inválido (ex: `model_year_end < model_year_start`) |

Formato:
```json
{ "detail": "manufacturer 99 not found" }
```

---

### Uso recomendado no formulário de criação de thread

Fluxo sugerido para o seletor de veículo:

1. `GET /manufacturers?limit=100` → popula dropdown de montadora
2. Ao selecionar montadora → `GET /vehicles?manufacturer_id={id}&is_current=true` → popula dropdown de modelo
3. Ao digitar → `GET /vehicles?manufacturer_id={id}&search={termo}` (debounce 300ms)
4. Filtro opcional de ano: `GET /vehicles?manufacturer_id={id}&year={ano_do_veiculo}`

O front deve gravar `manufacturer_name`, `model` e `model_year_start` no payload de criação da thread
(campos `vehicle_brand`, `vehicle_model`, `vehicle_year`).

---

## Área admin — Catálogos de peças (RAG)

Todos os endpoints desta seção exigem `X-Admin-Token: <token>`.

O fluxo tem duas etapas:
1. **Gerenciar catálogos** — upload de PDFs, acompanhar ingestão, remover.
2. **Consultar catálogos (RAG)** — pergunta em linguagem natural; a API retorna resposta gerada pelo LLM + trechos-fonte.

---

### `POST /admin/catalogs`

Faz upload de um PDF de catálogo de peças. A ingestão (extração de texto, chunking e geração de embeddings) ocorre em background — o endpoint responde `202` imediatamente.

Header obrigatório: `X-Admin-Token: <token>`
Content-Type: `multipart/form-data`

Campos do form:

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `file` | File (PDF) | sim | Arquivo PDF do catálogo |
| `manufacturer_id` | int | não | ID da montadora relacionada |
| `description` | string | não | Texto livre (ex: "Fiat Uno 1984–1997") |

Response `202`:
```json
{
  "id": 1,
  "manufacturer_id": 2,
  "original_filename": "catalogo-fiat-uno.pdf",
  "file_size_bytes": 30408704,
  "description": "Fiat Uno 1984–1997",
  "status": "pending",
  "page_count": null,
  "chunk_count": null,
  "error_message": null,
  "created_at": "2026-03-28T12:00:00Z",
  "updated_at": "2026-03-28T12:00:00Z"
}
```

Valores de `status`:

| Valor | Significado |
|---|---|
| `pending` | Aguardando início da ingestão |
| `processing` | Extraindo texto e gerando embeddings |
| `ready` | Pronto para consulta RAG |
| `error` | Falha na ingestão (ver `error_message`) |

Erros:
- `400` — arquivo enviado não é PDF

---

### `GET /admin/catalogs`

Lista todos os catálogos cadastrados.

Header obrigatório: `X-Admin-Token: <token>`

Query params:

| Param | Tipo | Descrição |
|---|---|---|
| `manufacturer_id` | int | Filtrar por montadora |
| `status` | string | Filtrar por status (`pending`, `processing`, `ready`, `error`) |
| `limit` | int (default 100) | Paginação |
| `offset` | int (default 0) | Paginação |

Response `200`:
```json
[
  {
    "id": 1,
    "manufacturer_id": 2,
    "original_filename": "catalogo-fiat-uno.pdf",
    "file_size_bytes": 30408704,
    "description": "Fiat Uno 1984–1997",
    "status": "ready",
    "page_count": 412,
    "chunk_count": 1380,
    "error_message": null,
    "created_at": "2026-03-28T12:00:00Z",
    "updated_at": "2026-03-28T12:05:30Z"
  }
]
```

---

### `GET /admin/catalogs/{catalog_id}`

Detalhe de um catálogo. Usar para polling de status pós-upload.

Header obrigatório: `X-Admin-Token: <token>`

Response `200`: mesmo shape do item do array acima.

Erros:
- `404` — catálogo não encontrado

---

### `DELETE /admin/catalogs/{catalog_id}`

Remove o catálogo, todos os seus chunks vetorizados e o arquivo PDF do disco.

Header obrigatório: `X-Admin-Token: <token>`

Response `204 No Content`.

Erros:
- `404` — catálogo não encontrado

---

### `POST /admin/catalogs/query`

Consulta RAG: busca trechos relevantes nos catálogos ingeridos e gera uma resposta via LLM.

Header obrigatório: `X-Admin-Token: <token>`
Content-Type: `application/json`

Request:
```json
{
  "query": "Qual o número da peça do filtro de óleo do Fiat Uno 1.0 1994?",
  "manufacturer_id": 2,
  "catalog_id": null,
  "top_k": 6
}
```

Campos:

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `query` | string (3–1000 chars) | sim | Pergunta em linguagem natural |
| `manufacturer_id` | int | não | Restringe a busca a catálogos desta montadora |
| `catalog_id` | int | não | Restringe a busca a um único catálogo |
| `top_k` | int (1–20, default 6) | não | Quantidade de trechos recuperados |

Response `200`:
```json
{
  "answer": "O filtro de óleo do Fiat Uno 1.0 1994 tem o número de peça 7700274199. Ele está listado na página 87 do catálogo como compatível com motores Fire 1.0 8V do período 1991–1997.",
  "sources": [
    {
      "catalog_id": 1,
      "filename": "catalogo-fiat-uno.pdf",
      "page": 87,
      "chunk_text": "Filtro de óleo completo - Cod. 7700274199 - Motor Fire 1.0 8V ...",
      "similarity": 0.91
    },
    {
      "catalog_id": 1,
      "filename": "catalogo-fiat-uno.pdf",
      "page": 88,
      "chunk_text": "Ver também filtro de combustível Cod. 7700868142 ...",
      "similarity": 0.74
    }
  ]
}
```

Campos da resposta:

| Campo | Tipo | Descrição |
|---|---|---|
| `answer` | string | Resposta gerada pelo LLM com base nos trechos |
| `sources` | array | Trechos usados como contexto |
| `sources[].catalog_id` | int | ID do catálogo de origem |
| `sources[].filename` | string | Nome original do PDF |
| `sources[].page` | int | Página do PDF onde o trecho foi extraído |
| `sources[].chunk_text` | string | Até 300 chars do trecho usado |
| `sources[].similarity` | float (0–1) | Score de similaridade coseno |

Nota: se não houver catálogos ingeridos ou nenhum trecho relevante for encontrado, `answer` trará uma mensagem explicando a ausência e `sources` será `[]`.

---

### Polling recomendado após upload

Após o `POST /admin/catalogs`, fazer polling em `GET /admin/catalogs/{id}` a cada **3 segundos** até que `status` seja `ready` ou `error`. Parar o polling em ambos os casos.

```
POST /admin/catalogs  →  status: "pending"
          ↓ (3s)
GET /admin/catalogs/1  →  status: "processing"
          ↓ (3s)
GET /admin/catalogs/1  →  status: "ready"  ✓
```

---

### Erros esperados (catálogos)

| Código | Quando |
|---|---|
| `400` | Arquivo não é PDF |
| `404` | Catálogo não encontrado |
| `422` | `query` muito curta/longa, `top_k` fora do intervalo |

Formato padrão:
```json
{ "detail": "mensagem de erro" }
```
