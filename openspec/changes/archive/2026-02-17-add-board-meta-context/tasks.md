## 1. Backend: UserMeta Pydantic schema

- [x] 1.1 Create `UserLocationMeta` and `UserMeta` Pydantic schemas in a shared location (e.g., `backend/app/domains/goals/schemas.py` or a new `backend/app/core/schemas.py`). Fields: `timezone` (str), `locale` (str), `current_datetime` (str), `location` (UserLocationMeta | None), `device_type` (str). `UserLocationMeta` has optional `city` and `country` strings.

## 2. Backend: Goal creation accepts user_meta

- [x] 2.1 Add optional `user_meta: UserMeta | None` field to `GoalCreate` schema in `backend/app/domains/goals/schemas.py`
- [x] 2.2 Update `create_goal()` in `backend/app/domains/goals/service.py` to store `user_meta` in `ai_context["user_meta"]` when provided. Override `current_datetime` with server UTC time. Capture client IP from request and store in `ai_context["user_meta"]["client_ip"]`.
- [x] 2.3 Update goal creation router in `backend/app/domains/goals/router.py` to extract client IP from `request.client.host` / `X-Forwarded-For` header and pass it to the service

## 3. Backend: Meta formatting utility for AI prompts

- [x] 3.1 Create `format_user_meta_block(user_meta: dict | None) -> str` utility in `backend/app/domains/ai/prompts/meta.py`. Returns formatted "User context:" text block or empty string if meta is None. Omit null fields (e.g., skip "Location" line if location is null).
- [x] 3.2 Write unit test for `format_user_meta_block` covering: full meta, meta without location, None meta input

## 4. Backend: Inject meta into AI prompts

- [x] 4.1 Update `QUESTIONS_USER_PROMPT` template in `backend/app/domains/ai/prompts/questions.py` to include `{user_context}` placeholder
- [x] 4.2 Update follow-up question prompt in `questions.py` to include `{user_context}` placeholder
- [x] 4.3 Update `SKELETON_USER_PROMPT` in `backend/app/domains/ai/prompts/generate_board.py` to include `{user_context}` placeholder
- [x] 4.4 Update `ENRICHMENT_USER_PROMPT` in `backend/app/domains/ai/prompts/enrich_task.py` to include `{user_context}` placeholder
- [x] 4.5 Update AI service functions that format these prompts to pass the `user_context` value from `format_user_meta_block()`:
  - Question generation in `backend/app/domains/ai/service.py` (or pipeline nodes)
  - Follow-up question generation
  - `generate_board_stream()` skeleton call in `backend/app/domains/ai/service.py`
  - Task enrichment calls in `backend/app/domains/ai/service.py`

## 5. Backend: Include user_meta in BoardResponse

- [x] 5.1 Add `user_meta: dict[str, Any] | None` field to `BoardResponse` in `backend/app/domains/boards/schemas.py`
- [x] 5.2 Update `_build_board_response()` in `backend/app/domains/boards/service.py` to read `user_meta` from the related goal's `ai_context` and include it in the response

## 6. Frontend: Collect and send user meta

- [x] 6.1 Create a `useUserMeta()` hook in `frontend/src/shared/hooks/` (or `frontend/src/features/goals/hooks/`) that collects: `timezone` from `Intl.DateTimeFormat().resolvedOptions().timeZone`, `locale` from `navigator.language`, `device_type` by checking viewport width or user agent, and optionally requests browser geolocation (non-blocking)
- [x] 6.2 For browser geolocation: use `navigator.geolocation.getCurrentPosition()` to get lat/lng, then reverse geocode to city/country (or send raw coords). If denied, set `location: null`.
- [x] 6.3 Update the goal creation form / `GoalCreate` mutation to include `user_meta` in the POST body
- [ ] 6.4 Regenerate Orval types/hooks after OpenAPI spec changes (`pnpm run generate` or equivalent)

## 7. Frontend: Display meta on board detail

- [x] 7.1 Add a `BoardMetaInfo` component in `frontend/src/features/board/components/` that renders generation context (date + location) from `user_meta` in the board response
- [x] 7.2 Integrate `BoardMetaInfo` into the board detail page / `DagView` component
- [x] 7.3 Handle null `user_meta` gracefully (don't render the component)

## 8. Testing

- [x] 8.1 Backend unit test: `format_user_meta_block()` utility (covered in 3.2)
- [x] 8.2 Backend integration test: `POST /api/goals` with `user_meta` — verify `ai_context` contains `user_meta` with server-set `current_datetime`
- [x] 8.3 Backend integration test: `POST /api/goals` without `user_meta` — verify backward compatibility
- [x] 8.4 Backend integration test: `GET /api/boards/:id` returns `user_meta` from related goal
- [x] 8.5 Frontend: verify `useUserMeta()` hook returns expected shape
- [x] 8.6 Frontend: verify `BoardMetaInfo` renders correctly with and without meta

## 9. Verification

- [x] 9.1 Run full backend test suite (`pytest`)
- [x] 9.2 Run frontend build and type check (`pnpm build`, `pnpm typecheck`)
- [x] 9.3 Run Biome lint on frontend (`pnpm lint`)
- [x] 9.4 Run Ruff lint on backend
- [ ] 9.5 Manual E2E test: create goal with meta -> generate board -> verify meta in prompts (check logs) and on board detail page
