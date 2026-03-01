# Mecanice — Project Context (for Copilot)

0) Repository scope (read first)
This repository is **the backend/API + WhatsApp bot** for Mecanice.

- ✅ In this repo:
  - Receive **mechanic messages via WhatsApp Webhooks** and keep WhatsApp as a **mechanic-only channel**.
  - ...
  - **Notify stores/vendors via web notifications** (webhooks/events) — **never** via WhatsApp.
  - Expose the **Seller API** consumed by the Seller Portal front-end.

- ❌ Not in this repo:
  - The **Seller Portal UI** (front-end) — it lives in a **separate, dedicated repository**.
  - Any web pages, components, or UX flows for vendors.

## 1) What this project is
**Mecanice** is a SaaS that helps **mechanics (workshops)** and **auto-parts stores** communicate faster and with less ambiguity when identifying the correct part for a vehicle under repair.

1.1 **WhatsApp channel constraint**:
   - WhatsApp is **mechanic-only**.
   - Never send quote requests, candidates, or follow-ups to stores/vendors via WhatsApp.
   - Store/vendor notifications must be via **web notifications** (webhooks/events) and the Seller Portal.

The core problem: mechanics often have only partial information (part number, measurements, photos, vehicle model/year/engine), and auto-parts stores respond with inconsistent formats (price, brand, availability, delivery time). This creates delays, wrong parts, rework, and wasted time.

### Key change in the workflow (important)
Originally, stores received quote requests directly on WhatsApp — but store attendants could receive multiple requests from multiple mechanics at the same time, causing confusion and wrong replies.

**New approach (current):**
- **Mechanic stays on WhatsApp** (simple and familiar).
- **Auto-parts stores answer in a web portal** (Seller Portal), where quotes are organized and tracked.
- Stores are **notified via webhook** when a new quote request is assigned to them.
- Each workshop has an **exclusive attendant (vendor) per partner store** to avoid “concurrency” issues inside larger stores.
**Hard rule:** WhatsApp is **exclusive to the mechanic**. Stores/vendors must **never** receive or reply to quotes via WhatsApp — only via the Seller Portal + web notifications.

This way, the mechanic still gets fast answers, but the store side operates with structure, ownership, and auditability.

- The Seller Portal (separate front-end repo) renders the vendor inbox by consuming this backend’s Seller API.

## 2) MVP goal (what must exist first)
**MVP focus:** “Mechanic sends a part number → system creates a quote request → partner stores respond in the Seller Portal → mechanic receives consolidated offers”.

### MVP scope
1. **Auto-parts store registration**
   - Name
   - Address (at least city/state; optionally full address)
   - Webhook URL (for new quote notifications)
   - Optional fields (recommended): business hours, delivery coverage, payment methods, store notes.

2. **Workshop (mechanic) registration**
   - Workshop name (or mechanic name)
   - Primary WhatsApp number (mechanic contact)

3. **Vendor (store attendant) registration**
   - Belongs to an AutoPartsStore
   - Login credentials for the Seller Portal (email + password, SSO later if needed)

4. **Exclusive vendor assignment (anti-confusion rule)**
   - For each **Workshop x AutoPartsStore**, there is **exactly one** assigned Vendor.
   - This ensures requests from a workshop always land in the same vendor inbox for that store.
   - (Early MVP can allow an admin to manage assignments manually.)

5. **Mechanic request (WhatsApp)**
   - Mechanic submits: part number (and optional free text like vehicle model/year/engine).
   - System creates a **QuoteRequest**.
   - System selects target stores (initially: all active stores or manual selection).
   - System runs LLM extraction to normalize request data when needed (e.g., split part number variants, normalize vehicle info).

6. **Dispatch to stores (web + webhook)**
   - For each selected store:
     - System creates a **QuoteInboxItem** (store-side view of the request).
     - System determines the assigned Vendor (Workshop x Store).
     - System sends a **webhook** to the store’s endpoint announcing the new quote request (idempotent).
   - The Seller Portal shows the request in the vendor’s inbox with all relevant details.

7. **Store response (Seller Portal)**
      - Vendor answers in the Seller Portal UI (separate repo), submitting a structured payload to this backend (Seller API):

8. **Consolidated result + notifications (to mechanic)**
   - Mechanic receives WhatsApp notifications as offers arrive:
     - “Store X responded: R$ 289, brand Y, delivery tomorrow…”
   - Mechanic can request a consolidated summary at any time:
     - best offers sorted by price/ETA/availability.

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
- Provide a timeline of requests and outcomes.

LLM + retrieval (RAG) can help:
- Extract structured data from messy mechanic messages.
- Normalize units/format (“R$ 250,00”, “250 reais”, “R$250”).
- Detect missing info and suggest follow-up questions.
- Reuse internal knowledge: previous quotes, part equivalences, common vehicle-part relations.

## 4) Key concepts (domain language)
- **Workshop**: mechanic / workshop entity (the requester).
- **AutoPartsStore**: store that receives requests and replies with offers (via Seller Portal).
- **Vendor**: a store attendant user that logs into the Seller Portal.
- **VendorAssignment**: exclusive mapping **(workshop_id, store_id) → vendor_id**.
- **QuoteRequest**: request for a part (MVP: part number) with context.
- **QuoteInboxItem**: store-side representation of a QuoteRequest assigned to a vendor.
- **QuoteOffer**: structured response from a vendor (price, brand, etc.).
- **NotificationEvent**: event emitted when a request is created or an offer is submitted (used for webhooks and WhatsApp notifications).
- **PartIdentifier**: string like OEM/aftermarket part number; may include variants.
- **VehicleInfo (optional)**: model/year/engine/trim notes.

## 5) System behavior rules (important)
1. **Never lose audit data**:
   - Store raw WhatsApp messages from mechanics.
   - Store raw vendor submissions and change history in the Seller Portal.

2. **Idempotency everywhere**:
   - Incoming WhatsApp webhooks can repeat.
   - Outgoing store webhooks may be retried.
   - Offer submissions must be safe to replay (avoid duplicates).

3. **Correlation keys**:
   - Every QuoteRequest has a `request_id`.
   - Every store-facing item includes `request_id` + `store_id` + `vendor_id`.
   - Every outgoing webhook includes an `event_id` (unique) + `request_id`.

4. **Exclusive vendor assignment is enforced**:
   - A workshop’s requests to a store must always land in the assigned vendor’s inbox.
   - Prevents wrong answers caused by multiple attendants replying out of context.

5. **Low cost is a hard constraint**:
   - Prefer serverless + managed services where possible.

## 6) Suggested architecture (high-level)
This project is designed to be clean and maintainable, with **clear separation of concerns**.

### Layers (hexagonal / clean-ish)
- **domain/**
  - Entities, value objects, domain services, domain rules
  - No framework/IO code here
- **app/** (application layer / use-cases)
  - Orchestrates domain + repositories + gateways
  - Use cases like:
    - CreateQuoteRequestFromWhatsApp
    - AssignVendorsAndCreateInboxItems
    - DispatchStoreWebhookNotification
    - SubmitQuoteOfferFromPortal
    - NotifyMechanicOnWhatsApp
    - BuildQuoteSummary
- **infrastructure/**
  - WhatsApp gateway client (Cloud API)
  - Webhook dispatcher (HTTP client + retry policy)
  - Persistence (e.g., DynamoDB)
  - Queue/event integration (if used)
  - LLM provider adapter

### API surfaces (drivers)
- **WhatsApp Webhook API** (mechanic → system)
- **Seller Portal API** (vendor → system)
- **Admin API** (manage stores/vendors/assignments)
- **Outbound Webhooks** (system → store systems / notifications)

## 7) Data storage (conceptual)
(Implementation can vary; keep the intent)

### Tables / collections (DynamoDB style mental model)
- `autoparts_stores`
  - store_id, name, address, webhook_url, active, metadata
- `workshops`
  - workshop_id, name, whatsapp_number, metadata
- `vendors`
  - vendor_id, store_id, name, email, role, active
- `vendor_assignments`
  - assignment_id, workshop_id, store_id, vendor_id, created_at
- `seller_credentials`
  - id, seller_id (FK vendors), autopart_id (FK autoparts), email (unique), password_hash, active, created_at, updated_at
- `quotations`
  - id, code, seller_id (FK vendors), workshop_id (FK workshops), part_number, part_description, vehicle_info, status (NEW/IN_PROGRESS/OFFERED/CLOSED), is_urgent, offer_submitted, soft_delete, created_at, updated_at
- `quote_requests`
  - request_id, workshop_id, part_number, vehicle_info, status, created_at
- `quote_inbox_items`
  - inbox_item_id, request_id, store_id, vendor_id, status, created_at, last_updated_at
- `quote_offers`
  - offer_id, request_id, store_id, vendor_id, price, brand, availability, delivery, notes, confidence, created_at
- `events`
  - event_id, type, request_id, store_id, vendor_id, payload, created_at, delivered_status
- `messages_raw`
  - message_id, request_id, direction(in/out), channel(whatsapp/portal/webhook), raw_payload, timestamps

### Seller Portal Authentication
- Sellers authenticate via `POST /seller/login` with email + password.
- Passwords are hashed with bcrypt in `seller_credentials`.
- Successful login returns a JWT (HS256, 8h expiry) containing `vendor_id` and `store_id`.
- All `/seller/*` endpoints (except `/seller/login` and `/seller/credentials`) require `Authorization: Bearer <jwt>`.

## 8) Store webhook contract (practical)
When a new request is assigned to a store/vendor, Mecanice sends a webhook to the store’s configured endpoint.

### Example outbound webhook (JSON)
- `event_type`: `"QUOTE_REQUEST_ASSIGNED"`
- `event_id`: unique UUID
- `request_id`: QuoteRequest identifier
- `store_id`: store receiving the request
- `vendor_id`: assigned vendor
- `part_number`: string
- `vehicle_info`: optional
- `created_at`: ISO datetime

Webhook delivery rules:
- Retry with backoff on non-2xx responses.
- Sign payloads (HMAC) when possible (later if needed).
- Store delivery attempts for audit.

## 9) AI usage guidelines (for code generation)
- AI extraction should produce a structured object, e.g.:
  - `part_number`: string
  - `vehicle_info`: string | null
  - `normalized_notes`: string | null
  - `confidence`: 0..1
- For vendor offers, prefer structured form data first.
  - Use LLM only to help interpret free-text notes (optional).
- Never overwrite raw text. Always store both.
- Keep prompts short and consistent; log model output (sanitized).

## 10) Coding conventions (important for Copilot)
- **English only** for:
  - file/folder names
  - variables/functions/classes
  - database keys/fields
- **Portuguese is allowed** for:
  - user-facing messages (errors/success messages shown to users)
- Prefer small, testable functions and explicit types.
- Use DTOs/schemas for request/response validation (Pydantic).
- Logging should include `request_id`, `store_id`, `vendor_id`, `inbox_item_id` whenever relevant.

## 11) What “done” looks like (MVP acceptance)
A mechanic can send a part number on WhatsApp, the system creates a QuoteRequest, assigns an exclusive vendor per store, notifies stores via webhook, vendors respond via the Seller Portal, and the mechanic receives consolidated structured offers — with full audit trails for messages, events, and offers.

---

If you are generating code for this repository:
- Keep business rules inside `domain/` and orchestration inside `app/`.
- Treat WhatsApp, webhooks, and persistence as adapters in `infrastructure/`.
- Always preserve raw payloads and make processing idempotent.
