# P0 Acceptance Checklist

## Result conventions

- `PASS`: executed and met the expected result.
- `FAIL`: executed and did not meet the expected result.
- `NOT_RUN`: a conditional test could not run, normally because no real key exists.

## Functional P0

- [ ] With all provider keys empty, backend and frontend start successfully.
- [ ] `/api/v1/health/live` returns HTTP 200.
- [ ] `/api/v1/health/ready` returns HTTP 200 and includes Provider states.
- [ ] Mock non-streaming chat returns a normalized response and usage.
- [ ] Mock streaming emits `meta → delta+ → done` with continuous sequence numbers.
- [ ] The web UI renders a multi-turn Mock conversation.
- [ ] The history sidebar can be hidden and restored without losing conversation state.
- [ ] “管理模型” remains available before and after the first message without clearing conversation state.
- [ ] The configuration dialog edits API Key, Base URL and independent model rows for each real Provider.
- [ ] Models can be added and deleted; empty and duplicate model names are rejected.
- [ ] One selected model can test unsaved API Key and Base URL values without saving configuration or history.
- [ ] Connection results distinguish authentication, payment, invalid request, rate limit, timeout and upstream failures.
- [ ] Saving preserves the current model when present and falls back to the first model only when it was removed.
- [ ] Editing a non-active Provider does not switch the active conversation Provider.
- [ ] “允许联网搜索” is off by default and can be changed during an existing conversation.
- [ ] When enabled, the final user message is searched before the Provider request.
- [ ] Bing RSS failure falls back to DuckDuckGo HTML parsing.
- [ ] Search context contains real source URLs and is marked as untrusted external material.
- [ ] Search failure returns `WEB_SEARCH_FAILED` instead of claiming that current information was retrieved.
- [ ] V1.4 conversation databases migrate with web search disabled by default.
- [ ] Saving a runtime configuration immediately refreshes Provider status and model selection.
- [ ] A conversation is automatically saved to SQLite before the first provider call.
- [ ] History survives a backend restart and restores messages and generation settings.
- [ ] History supports search, rename, confirmed deletion and time grouping.
- [ ] The configuration dialog opens immediately while backend configuration is loading.
- [ ] An old backend is reported as a compatibility error instead of a non-responsive button.
- [ ] The document body never scrolls; history and message areas scroll independently.
- [ ] The composer remains visible at the bottom at 1366×768 and 1920×1080.
- [ ] The user can stop an active generation and keep the partial answer.
- [ ] OpenAI and Anthropic appear as unconfigured instead of crashing startup.
- [ ] A mismatched or unknown model is rejected before an upstream call.
- [ ] Validation failures use the normalized ErrorResponse.
- [ ] Provider authentication, rate limit, timeout and upstream errors are normalized.
- [ ] OpenAI request/response/stream contract tests pass offline.
- [ ] Anthropic request/response/stream contract tests pass offline.
- [ ] The frontend production build and TypeScript check pass.
- [ ] Backend tests pass with total coverage of at least 70% and core coverage of at least 80%.
- [ ] `.env`, browser traffic, API responses and application logs contain no provider key.
- [ ] `/docs` exposes every API endpoint and schema.

## Reproduction

### Local

1. Copy `.env.example` to `.env` without adding keys.
2. Create the backend Python 3.12 virtual environment.
3. Install `backend` with its `dev` dependencies and run pytest.
4. Install `frontend`, run unit tests, typecheck and production build.
5. Start FastAPI on port 8000 and Next.js on port 3000.
6. Send one streaming Mock message in the browser.
7. Stop one longer streaming response before completion.
8. Select OpenAI and confirm that the UI says it is not configured.

### Docker

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Wait until the backend health check passes.
4. Open `http://localhost:3000` and complete one Mock conversation.

## Conditional online verification

These items are not P0 gates:

| Provider | Non-stream | Stream | Status without key |
|---|---|---|---|
| OpenAI | Minimal response and usage | At least one delta and terminal event | `NOT_RUN` |
| Anthropic | Minimal response, system prompt applied | At least one delta and terminal event | `NOT_RUN` |
| DeepSeek | Compatible request succeeds | Compatible stream succeeds | `NOT_RUN` |

The final report must not label a Provider `live-verified` unless its own real key was used successfully.

## Security review

- [ ] `.gitignore` excludes `.env`, virtual environments, build output and test reports.
- [ ] Frontend source and build output contain no key variable value.
- [ ] Only the dedicated localhost configuration endpoint can change a Base URL; remote HTTP URLs are rejected.
- [ ] Runtime configuration responses expose only `api_key_configured`, never the key or a key fragment.
- [ ] CORS permits only configured origins.
- [ ] Prompt/completion bodies are absent from default logs.
- [ ] Oversized messages and output limits are rejected before provider access.
- [ ] README states that public deployment requires authentication and rate limiting.

## Recorded local validation

Fill this table after running the final version:

| Check | Result | Notes |
|---|---|---|
| Backend pytest | `PASS` | 25 tests passed |
| Backend coverage | `PASS` | Total 83% |
| Frontend unit tests | `PASS` | 5 tests passed across 2 files |
| Frontend typecheck | `PASS` | TypeScript no errors |
| Frontend lint | `PASS` | ESLint no errors or warnings |
| Frontend production build | `PASS` | Next.js production build completed |
| Local frontend startup | `PASS` | HTML served successfully on local port |
| Local backend startup | `PASS` | Health, JSON chat and SSE chat verified |
| Browser Mock E2E | `NOT_RUN` | User chose to skip; browser binary unavailable in validation environment |
| Public search live smoke | `NOT_RUN` | Validation environment blocks public search domains; parser, fallback and enrichment paths are covered offline |
| Docker Compose | `NOT_RUN` | Docker executable unavailable in validation environment; configuration parsed statically |
| OpenAI live smoke | `NOT_RUN` | No key by default |
| Anthropic live smoke | `NOT_RUN` | No key by default |
| DeepSeek live smoke | `NOT_RUN` | No key by default |
