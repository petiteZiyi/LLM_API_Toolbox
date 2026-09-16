# Changelog

## 1.5.0

- Added an “允许联网搜索” conversation switch in generation settings.
- Added no-key experimental web search with Bing RSS and DuckDuckGo HTML fallback.
- Search-enabled requests retrieve current results before calling OpenAI, Anthropic or DeepSeek.
- Search context is marked as untrusted external material and includes source URLs for citation.
- Added normalized search-unavailable errors instead of silently pretending a search succeeded.
- Persisted the search switch per conversation with automatic migration of V1.4 SQLite databases.

## 1.4.0

- Added an always-available “管理模型” entry beside the Provider and model selectors.
- Rebuilt model editing as independent rows with add, delete and test-model selection controls.
- Added non-persistent connection testing for one selected model, including unsaved form values.
- Added explicit authentication, balance, invalid-request, rate-limit, timeout and upstream test results.
- Provider configuration changes now preserve the current model when it still exists.
- Editing another Provider no longer switches the active conversation away from its current Provider.
- Included the V1.3.1 PATCH/DELETE CORS fix for multi-turn conversations and history deletion.

## 1.3.1

- Fixed browser CORS preflight failures when updating an existing conversation with `PATCH`.
- Fixed browser CORS preflight failures when deleting conversations with `DELETE`.
- Added a regression test covering browser conversation-update preflight requests.
- Updated the built-in DeepSeek Base URL and model defaults to the current official API values.

## 1.3.0

- Added local SQLite conversation persistence with automatic titles.
- Added history listing, time grouping, search, loading, renaming and deletion.
- Rebuilt the interface in a restrained light ChatGPT/Claude-style layout.
- Fixed the page-height bug with independent sidebar and conversation scrolling.
- Moved Provider/model selection to the header and advanced parameters to a dialog.
- Configuration dialogs now open immediately and show loading, offline or outdated-backend states.
- Added explicit frontend/backend API compatibility detection.
- Added conversation CRUD, persistence and compatibility API tests.

## 1.2.0

- Refined the desktop workbench visual system, typography, spacing and surfaces.
- Added a clearer live Provider/model status card in the session header.
- Redesigned the welcome state, message presentation and floating composer.
- Improved sidebar controls, form states, modal depth and mobile responsiveness.
- Replaced decorative text glyphs with consistent inline interface icons.

## 1.1.0

- Added a collapsible model settings sidebar with a persistent restore control.
- Added a Provider configuration dialog for API keys, Base URLs and model lists.
- Added backend-only, in-memory runtime configuration endpoints for OpenAI, Anthropic and DeepSeek.
- API keys are never returned, logged, or stored in browser persistence.
- Runtime Provider and model state refresh immediately after saving.
- Clarified that Mock is an echo-only test Provider rather than an intelligent model.
- Added runtime configuration security and API tests.
