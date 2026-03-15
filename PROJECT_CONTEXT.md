# Mecanice Backend Project Context

## Current product truth
Mecanice’s backend powers an internal browser-based quotation workflow between mechanics and auto parts sellers.

- Mechanics create a request for one or more parts.
- The system opens a quotation thread.
- The system may store optional suggested parts.
- Sellers answer inside the platform, not through WhatsApp.
- Sellers can build offers by selecting suggested parts and/or manually adding compatible items.
- Each offer is itemized and priced per item.
- Mechanics compare submitted offers in a normalized view.

## MVP rules
- No WhatsApp integration in the MVP flow.
- No external messaging provider dependency in the core workflow.
- Chat is internal and browser-based.
- Suggestions are assistive only.
- Manual item inclusion by the seller is mandatory.
- Suggested parts and offered items are different domain concepts and must stay separated.

## Main entities
- `mechanics`
- `workshops`
- `autoparts`
- `vendors`
- `vendor_assignments`
- `quote_threads`
- `part_requests`
- `thread_messages`
- `suggested_parts`
- `seller_offers`
- `seller_offer_items`

## API direction
The main API surface is organized around:
- auth/session
- threads
- messages
- suggestions
- offers
- comparison
- seller inbox read model

## Architectural guidance
- Keep FastAPI routers thin.
- Keep business rules inside repository/service boundaries that are easy to test.
- Prefer straightforward REST + polling.
- Avoid reintroducing WhatsApp-specific workflow assumptions into new features.
- Preserve auditability for request text, offer items, and offer submission moments.

## Validation and authorization rules
- Mechanics can only access their own threads and comparison views.
- Sellers can only access threads visible to their shop/assignment and can only change their own offers.
- Submitted offers must have at least one item.
- Offer items must have positive quantity and positive price at submission time.
- Suggestion-linked offer items must copy title/brand/part number into the offer item record.

## Implementation note
Legacy tables and modules from the previous WhatsApp-centered flow can remain in the repository, but the browser-first thread workflow is the source of truth for the MVP.
