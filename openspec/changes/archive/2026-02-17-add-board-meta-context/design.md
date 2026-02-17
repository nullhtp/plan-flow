## Context

The AI pipeline currently generates boards and questions using only goal text, classification data, and Q&A pairs. It has no awareness of the user's timezone, location, current date, locale, or device type. This means the AI cannot set realistic due dates (it doesn't know "today"), suggest location-relevant tasks, or adapt task granularity to the user's device.

This change adds automatic collection of user environment metadata ("user meta") at goal creation time, passes it through the AI pipeline for both question generation and board generation, and makes it available for display on the board detail page.

## Goals / Non-Goals

- Goals:
  - Collect timezone, locale, current datetime, geolocation, and device type automatically
  - Store meta in `Goal.ai_context["user_meta"]` as the single source of truth
  - Inject meta into all AI prompts (question generation, follow-up questions, board skeleton, task enrichment)
  - Display meta context on the board detail page (read from the related goal)
  - Use browser Geolocation API with IP-based fallback for location

- Non-Goals:
  - User profile / settings page for meta preferences (future)
  - Cross-goal intelligence / past boards summary (separate feature)
  - Currency detection or financial context (could be derived from locale later)
  - Precise GPS coordinates (we only need city/country level)

## Decisions

### Decision 1: Single storage in Goal.ai_context

Meta is stored in one place only: `Goal.ai_context["user_meta"]`, written at goal creation time.

**Why:**
- `Goal.ai_context` already accumulates pipeline context (classification, questions, answers). Adding `user_meta` is consistent with this pattern.
- Both question generation and board generation already read from `Goal.ai_context` — no new data path needed.
- The board detail page can access meta via the board's related goal (the board already has a `goal_id` FK). The `BoardResponse` can include `user_meta` as a computed field read from the goal at query time — no separate DB column required.
- Avoids dual storage, stale-copy issues, and an unnecessary Alembic migration.

**Alternative considered:** Add a `meta` JSON column to the Board model and copy meta from `Goal.ai_context` at board generation time. Rejected because it duplicates data, requires a migration, and the board always has access to its goal.

### Decision 2: Frontend collects meta, sends in request body

The frontend collects all client-side meta (timezone, locale, device type, geolocation) and sends it in the `POST /api/goals` request body as a `user_meta` object. The backend also captures the client IP from request headers for geolocation fallback.

**Why:** Timezone, locale, and device type are only available client-side. Geolocation via browser API is also client-side. This keeps the backend stateless — it doesn't need to maintain user preferences or browser sessions.

**Alternative considered:** Backend-only collection using IP geolocation for everything. Rejected because timezone and locale detection from IP is unreliable (VPNs, proxies), and the browser has authoritative data.

### Decision 3: Browser Geolocation API with IP fallback

1. On the goal creation page, request browser Geolocation API permission (non-blocking)
2. If granted: send `{ city, country }` resolved via reverse geocoding or just lat/lng for server-side resolution
3. If denied/unavailable: backend uses client IP from `X-Forwarded-For` or `request.client.host` for coarse city/country resolution
4. IP geolocation: extract IP from request headers only, no external API calls or local GeoIP database. Store the raw IP. Resolution can be added later if needed.

**Why:** Browser API gives most accurate location. IP fallback ensures we always have something. Storing raw IP without resolution keeps the implementation minimal — no external API dependency, no GeoIP database to maintain.

**Alternative considered:** External IP geolocation API (ip-api.com). Rejected to avoid external dependency and added latency. Can be added later as an enhancement.

### Decision 4: Meta schema

```python
class UserLocationMeta(BaseModel):
    city: str | None = None
    country: str | None = None

class UserMeta(BaseModel):
    timezone: str                    # IANA timezone (e.g., "Europe/Berlin")
    locale: str                      # BCP 47 locale (e.g., "en-US", "de-DE")
    current_datetime: str            # ISO 8601 UTC (e.g., "2026-02-17T14:30:00Z")
    location: UserLocationMeta | None = None  # From browser or IP
    device_type: str                 # "mobile" | "desktop" | "tablet"
```

**Why:** Minimal but sufficient. Location is optional (may be denied). No lat/lng or country_code — just human-readable city/country for prompt injection. `current_datetime` is set server-side at goal creation to ensure consistency (client clocks may drift).

### Decision 5: Prompt injection strategy

Meta is appended as a new section in the user prompt (not the system prompt) for:
- Question generation (`prompts/questions.py`)
- Follow-up question generation (`prompts/questions.py`)
- Board skeleton generation (`prompts/generate_board.py`)
- Task enrichment (`prompts/enrich_task.py`)

Format in prompts:
```
User context:
- Timezone: Europe/Berlin
- Locale: de-DE
- Current date: 2026-02-17
- Location: Berlin, Germany
- Device: desktop
```

**Why:** User prompt is the right place for contextual data (system prompt defines behavior). Consistent format across all prompts. Only include fields that have values (skip null location, etc.).

### Decision 6: Frontend display

Show a small info section on the board detail page with the generation context. Example: "Generated on Feb 17, 2026 | Berlin, Germany". Non-intrusive, informational only. The frontend reads `user_meta` from the `BoardResponse` (which the backend computes from the related goal's `ai_context`).

## Risks / Trade-offs

- **Geolocation permission popup UX** — Users may deny location permission. Mitigation: non-blocking request, graceful fallback to IP, clear explanation of why location helps.
- **IP fallback stores raw IP only** — No actual geolocation resolution from IP in this change. The meta `location` field will be null if browser geolocation is denied. Mitigation: acceptable for MVP; IP-to-location resolution can be added as a follow-up.
- **Prompt length increase** — Adding ~5 lines of meta to each prompt. Negligible impact on token usage and latency.
- **Extra query for board response** — `BoardResponse` needs to read `user_meta` from the related Goal. The board query already joins/loads the goal relationship, so this adds no extra DB round-trip.

## Migration Plan

No database migration required. The `Goal.ai_context` JSON column already exists and is schema-less — adding a `user_meta` key requires no DDL changes.

Backward compatibility:
- If `user_meta` is not in the request body, goal creation still works (meta is optional)
- If `Goal.ai_context` has no `user_meta`, AI prompts omit the "User context" block
- If `user_meta` is absent, the board detail page simply doesn't show the meta section

## Open Questions

- None — all questions resolved during proposal discussion.
