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
