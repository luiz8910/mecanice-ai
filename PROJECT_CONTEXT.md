# Mecanice — Project Context (for Copilot)

## 1) What this project is
**Mecanice** is a SaaS that helps **mechanics** and **auto-parts stores** communicate faster and with less ambiguity when identifying the correct part for a vehicle under repair.

The core problem: in real life, mechanics often have only partial information (part number, measurements, photos, vehicle model/year/engine), and auto-parts stores respond with inconsistent formats (price, brand, availability, delivery time). This creates delays, wrong parts, rework, and wasted time on WhatsApp back-and-forth.

Mecanice centralizes and automates this flow:
- A mechanic submits a **part request** (MVP: part number; later: photo + measurements + vehicle details).
- The system broadcasts that request to multiple auto-parts stores (via WhatsApp Cloud API or equivalent).
- The system captures attendants’ replies and **converts them into structured quotes**.
- The mechanic receives a **consolidated “best options” view** (price, brand, availability, delivery, notes), without manually chasing each store.

## 2) MVP goal (what must exist first)
**MVP focus:** “Send a part number to a list of stores and return a consolidated quote”.

### MVP scope
1. **Auto-parts store registration**
   - Name
   - Primary WhatsApp number
   - Address (at least city/state; optionally full address)
   - Optional fields (recommended): secondary WhatsApp, business hours, delivery coverage, payment methods, contact person, store notes.

2. **Mechanic request**
   - Mechanic submits: part number (and optional free text like vehicle model/year/engine).
   - System creates a QuoteRequest.
   - System selects target stores (initially manual selection / all active stores).

3. **Broadcast + capture**
   - Bot sends a standardized WhatsApp message with:
     - Part number
     - (Optional) vehicle info / notes
     - A request identifier (tracking ID) to correlate replies.
   - System receives attendants’ replies, links them to the request, and stores raw messages.

4. **Normalize responses into structured QuoteOffers**
   - Extract: price, brand, SKU/part number confirmation, availability, delivery time, pickup/delivery, warranty/notes.
   - Keep both:
     - **raw message** (audit/debug)
     - **structured fields** (for ranking and UI)

5. **Consolidated result**
   - Show mechanic a summary list (offers) and the original conversation per store.

### MVP non-goals (explicitly out-of-scope for now)
- Full catalog ingestion and “guaranteed compatibility” database.
- Automatic vehicle fitment across all brands/models.
- Payments inside the platform.
- Complex negotiation workflow (counter-offers, installments, etc.).
- Video support inside the platform (not required now).

## 3) Long-term objective (direction)
After MVP is stable, Mecanice evolves toward **part identification assistance**:
- Identify the correct part from **photos**, **measurements**, and **vehicle details**.
- Suggest likely compatible alternatives (“multi-brand equivalents”).
- Rank stores/offers by best match + price + delivery + reliability.
- Provide a history/timeline of requests and outcomes.

This is where LLM + retrieval (RAG) can help:
- Extract structured data from messy WhatsApp messages.
- Normalize units/format (“R$ 250,00”, “250 reais”, “R$250”).
- Detect missing info and suggest follow-up questions.
- (Later) use internal knowledge base: previous quotes, part equivalences, common vehicle-part relations.

## 4) Key concepts (domain language)
- **Mechanic**: user who requests parts/quotes.
- **AutoPartsStore**: store that receives requests and replies with offers.
- **QuoteRequest**: a request for a part (MVP: part number) with context.
- **Conversation**: message thread between system and a store for one request.
- **Message**: inbound/outbound WhatsApp message (raw payload + normalized fields).
- **QuoteOffer**: structured interpretation of a store reply.
- **PartIdentifier**: string like OEM/aftermarket part number; may include variants.
- **VehicleInfo (optional)**: model/year/engine/trim notes.

## 5) System behavior rules (important)
1. **Never lose raw messages**: store the original text/payload for traceability.
2. **Idempotency**: inbound webhooks can repeat; processing must be safe to re-run.
3. **Correlation**: every outbound request must carry a tracking identifier to link replies to QuoteRequest.
4. **Human-in-the-loop is allowed** (especially early):
   - If extraction is uncertain, keep it as “unparsed” and allow manual review.
5. **Low cost** is a hard constraint (budget-conscious infra decisions).

## 6) Suggested architecture (high-level)
This project is designed to be clean and maintainable, with **clear separation of concerns**.

### Layers (hexagonal / clean-ish)
- **domain/**
  - Entities, value objects, domain services, domain rules
  - No framework/IO code here
- **app/** (application layer / use-cases)
  - Orchestrates domain + repositories + gateways
  - Use cases like: CreateQuoteRequest, BroadcastQuoteRequest, IngestInboundMessage, BuildQuoteSummary
- **infrastructure/**
  - WhatsApp gateway client (Cloud API)
  - Persistence (e.g., DynamoDB)
  - Queue/event integration (if used)
  - External services adapters (LLM provider, etc.)
  
Note: the project is intended to follow this hexagonal structure, but the actual repository layout may differ; treat this as architectural guidance rather than a guaranteed directory listing.
Example layout that fits this architecture:
- `domain/` — pure domain entities and ports (interfaces/protocols).
- `app/` — use-cases (application services), FastAPI routers and wiring.
- `infrastructure/` — concrete adapters such as persistence repositories and messaging/WhatsApp integration.

Example supporting infrastructure you might introduce:
- `docker-compose.yml` and helper scripts (for running local databases such as Postgres+pgvector, if used)
- Database migrations to create tables for quote requests, conversations, messages, and quote offers
- Application-layer use case modules for actions like creating/broadcasting quotes and ingesting inbound messages

This organization keeps domain rules IO-free and makes swapping adapters easier (e.g., Postgres -> DynamoDB).
- (Optional) **interfaces/** or **api/**
  - FastAPI endpoints: webhooks, admin endpoints, health checks

### Tech direction (current)
- **Python + FastAPI** (API)
- **WhatsApp integration** (Cloud API / webhook)
- **AWS-first mindset** (because cost + portability)
  - Likely components: Lambda, DynamoDB, SQS (or equivalent), CloudWatch logs
- Local dev may use Docker for convenience, but production aims for AWS-managed components.

## 7) Data storage (conceptual)
(Implementation can vary; keep the intent)

### Tables / collections (DynamoDB style mental model)
- `autoparts_stores`
  - store_id, name, whatsapp_number, address, active, metadata
- `mechanics`
  - mechanic_id, name, contact, metadata
- `quote_requests`
  - request_id, mechanic_id, part_number, vehicle_info, status, created_at
- `conversations`
  - conversation_id, request_id, store_id, status, last_message_at
- `messages`
  - message_id, conversation_id, direction(in/out), raw_payload, text, timestamps, parsed_fields
- `quote_offers`
  - offer_id, request_id, store_id, extracted_price, brand, availability, delivery, confidence, raw_message_id

## 8) WhatsApp message formats (practical)
Outbound message should be consistent to maximize response quality.

Example outbound template:
- Part number: {part_number}
- Vehicle (optional): {vehicle_info}
- Please reply with: price, brand, availability, delivery time
- Tracking: {request_id}

Inbound messages can be unstructured; extraction should be tolerant:
- “Tenho por 289, marca X, entrega amanhã”
- “Só encomenda, chega em 3 dias”
- “Não tenho, mas tenho similar…”

## 9) AI usage guidelines (for code generation)
- AI extraction should produce a structured object, e.g.:
  - `price`: number or null
  - `currency`: "BRL"
  - `brand`: string or null
  - `availability`: enum (IN_STOCK / ORDER / OUT_OF_STOCK / UNKNOWN)
  - `delivery_eta`: string or normalized duration
  - `notes`: free text
  - `confidence`: 0..1
- Never overwrite raw text. Always store both.
- Prefer deterministic parsing first (regex/heuristics) + fallback to LLM when needed.
- Keep prompts short and consistent; log the model output (sanitized).

## 10) Coding conventions (important for Copilot)
- **English only** for:
  - file/folder names
  - variables/functions/classes
  - database keys/fields
- **Portuguese is allowed** for:
  - user-facing messages (errors/success messages shown to users)
- No `src/` folder. Use root-level folders:
  - `app/`, `domain/`, `infrastructure/` at the repository root
- Prefer small, testable functions and explicit types.
- Use DTOs/schemas for request/response validation (Pydantic).
- Logging should include `request_id`, `store_id`, `conversation_id` whenever relevant.

## 11) What “done” looks like (MVP acceptance)
A request with a part number can be created, broadcast to multiple stores, replies are captured, and the system returns a consolidated list of structured offers — while retaining the full message history per store.

---

If you are generating code for this repository:
- Keep business rules inside `domain/` and orchestration inside `app/`.
- Treat WhatsApp and persistence as adapters in `infrastructure/`.
- Always preserve raw messages and make processing idempotent.
