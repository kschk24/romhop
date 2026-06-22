---
id: TASK-035
title: >-
  Error message when trying to Pull savegames for "Sonic Advance", api key has
  to be re-set after
status: Done
assignee:
  - '@claude'
created_date: '2026-06-17 15:47'
updated_date: '2026-06-22 17:06'
labels:
  - bug
  - release-blocker
  - ready-for-agent
dependencies: []
priority: high
ordinal: 47000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Error: "Client error '404 Not Found' for url 'http://romm.batsnest.de/api/states/14/content'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/404 "

have checked in CLI aswell, here:
 "romhop -v pull "Sonic Advance"
2026-06-17 17:48:44,232 INFO romhop.config: settings loaded from /home/kschi/.config/romhop/settings.ini
2026-06-17 17:48:44,232 INFO romhop.config: settings loaded from /home/kschi/.config/romhop/settings.ini
2026-06-17 17:48:44,256 DEBUG httpcore.connection: connect_tcp.started host='<romm-host>' port=80 local_address=None timeout=60.0 socket_options=None
2026-06-17 17:48:44,269 DEBUG httpcore.connection: connect_tcp.complete return_value=<httpcore._backends.sync.SyncStream object at 0x7f5ef81e70e0>
2026-06-17 17:48:44,269 DEBUG httpcore.http11: send_request_headers.started request=<Request [b'GET']>
2026-06-17 17:48:44,269 DEBUG httpcore.http11: send_request_headers.complete
2026-06-17 17:48:44,269 DEBUG httpcore.http11: send_request_body.started request=<Request [b'GET']>
2026-06-17 17:48:44,269 DEBUG httpcore.http11: send_request_body.complete
2026-06-17 17:48:44,269 DEBUG httpcore.http11: receive_response_headers.started request=<Request [b'GET']>
2026-06-17 17:48:44,430 DEBUG httpcore.http11: receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Wed, 17 Jun 2026 15:48:44 GMT'), (b'Content-Type', b'application/json'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Content-Encoding', b'gzip'), (b'Server', b'cloudflare'), (b'vary', b'Accept-Encoding'), (b'x-served-by', b'<romm-host>'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=0RmTpsl0jdGZ6XdVY%2BCUkk%2Bey6tWkF5%2FbYBEBdwd4XyxXxUm8HnZ3veGgBv%2BNndidKO0uo%2Fuuf6H404SmmOkSf%2BFzM8MhqnBHuxk%2F8%2B6uMHGhLoMA%2Fjey9izS7ZAPzpxhmfG8OzMqtPqLPn2xJDs"}]}'), (b'CF-RAY', b'a0d33340b8c162b9-HAM'), (b'alt-svc', b'h3=":443"; ma=86400')])
2026-06-17 17:48:44,430 INFO httpx: HTTP Request: GET http://romm.batsnest.de/api/saves?rom_id=266 "HTTP/1.1 200 OK"
2026-06-17 17:48:44,430 DEBUG httpcore.http11: receive_response_body.started request=<Request [b'GET']>
2026-06-17 17:48:44,431 DEBUG httpcore.http11: receive_response_body.complete
2026-06-17 17:48:44,431 DEBUG httpcore.http11: response_closed.started
2026-06-17 17:48:44,431 DEBUG httpcore.http11: response_closed.complete
2026-06-17 17:48:44,431 DEBUG httpcore.http11: send_request_headers.started request=<Request [b'GET']>
2026-06-17 17:48:44,431 DEBUG httpcore.http11: send_request_headers.complete
2026-06-17 17:48:44,431 DEBUG httpcore.http11: send_request_body.started request=<Request [b'GET']>
2026-06-17 17:48:44,431 DEBUG httpcore.http11: send_request_body.complete
2026-06-17 17:48:44,431 DEBUG httpcore.http11: receive_response_headers.started request=<Request [b'GET']>
2026-06-17 17:48:44,512 DEBUG httpcore.http11: receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Wed, 17 Jun 2026 15:48:44 GMT'), (b'Content-Type', b'text/plain; charset=utf-8'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'content-disposition', b"attachment; filename*=utf-8''Sonic%20Advance%20%28USA%29%20%28En%2CJa%29.state"), (b'Content-Encoding', b'gzip'), (b'etag', b'W/"0cf07876438985d7ded1b3ec3a668c0a"'), (b'last-modified', b'Tue, 16 Jun 2026 12:49:21 GMT'), (b'Server', b'cloudflare'), (b'vary', b'Accept-Encoding'), (b'x-served-by', b'<romm-host>'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=s0wNF8EIu4hDCXGQyTofYir8NFX0R60zrsLxRQU8ueoYMqspF1P6xrju%2FzORbbRCwVkmqqNW4tB1PetAKOAzVCsrHXwto8RRe5%2F66insC042zo4h%2FCOu0DCY6F%2BoM7kjL%2F3xjumWz0xmGVsAa%2BBb"}]}'), (b'CF-RAY', b'a0d33341b9d862b9-HAM'), (b'alt-svc', b'h3=":443"; ma=86400')])
2026-06-17 17:48:44,512 INFO httpx: HTTP Request: GET http://romm.batsnest.de/api/saves/5/content "HTTP/1.1 200 OK"
2026-06-17 17:48:44,512 DEBUG httpcore.http11: receive_response_body.started request=<Request [b'GET']>
2026-06-17 17:48:44,517 DEBUG httpcore.http11: receive_response_body.complete
2026-06-17 17:48:44,517 DEBUG httpcore.http11: response_closed.started
2026-06-17 17:48:44,517 DEBUG httpcore.http11: response_closed.complete
2026-06-17 17:48:44,517 DEBUG httpcore.http11: send_request_headers.started request=<Request [b'GET']>
2026-06-17 17:48:44,517 DEBUG httpcore.http11: send_request_headers.complete
2026-06-17 17:48:44,517 DEBUG httpcore.http11: send_request_body.started request=<Request [b'GET']>
2026-06-17 17:48:44,517 DEBUG httpcore.http11: send_request_body.complete
2026-06-17 17:48:44,517 DEBUG httpcore.http11: receive_response_headers.started request=<Request [b'GET']>
2026-06-17 17:48:44,594 DEBUG httpcore.http11: receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Wed, 17 Jun 2026 15:48:44 GMT'), (b'Content-Type', b'text/plain; charset=utf-8'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'content-disposition', b"attachment; filename*=utf-8''Sonic%20Advance%20%28USA%29%20%28En%2CJa%29.srm"), (b'Content-Encoding', b'gzip'), (b'etag', b'W/"7cc3f583582c6b4a00cfa3e6c627715c"'), (b'last-modified', b'Wed, 17 Jun 2026 15:39:04 GMT'), (b'Server', b'cloudflare'), (b'vary', b'Accept-Encoding'), (b'x-served-by', b'<romm-host>'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=XZ1feoTA7zZv9a9R1cIHwTj3MYgPYsgG5ut8HHKGIAQJxUrF4%2F6sUXfqwjz6Qk1RMWkSmRoV6SmwHJOp4SN%2Fm%2Fn9TXGKXBAqDKhs9kyup2esBubG2K4WH%2B5Ie8bnW4NaEheyMMIChWiemghb6%2FX4"}]}'), (b'CF-RAY', b'a0d333424a5d62b9-HAM'), (b'alt-svc', b'h3=":443"; ma=86400')])
2026-06-17 17:48:44,594 INFO httpx: HTTP Request: GET http://romm.batsnest.de/api/saves/4/content "HTTP/1.1 200 OK"
2026-06-17 17:48:44,594 DEBUG httpcore.http11: receive_response_body.started request=<Request [b'GET']>
2026-06-17 17:48:44,596 DEBUG httpcore.http11: receive_response_body.complete
2026-06-17 17:48:44,596 DEBUG httpcore.http11: response_closed.started
2026-06-17 17:48:44,597 DEBUG httpcore.http11: response_closed.complete
2026-06-17 17:48:44,597 DEBUG httpcore.http11: send_request_headers.started request=<Request [b'GET']>
2026-06-17 17:48:44,597 DEBUG httpcore.http11: send_request_headers.complete
2026-06-17 17:48:44,597 DEBUG httpcore.http11: send_request_body.started request=<Request [b'GET']>
2026-06-17 17:48:44,597 DEBUG httpcore.http11: send_request_body.complete
2026-06-17 17:48:44,597 DEBUG httpcore.http11: receive_response_headers.started request=<Request [b'GET']>
2026-06-17 17:48:44,672 DEBUG httpcore.http11: receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Wed, 17 Jun 2026 15:48:44 GMT'), (b'Content-Type', b'application/json'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Content-Encoding', b'gzip'), (b'Server', b'cloudflare'), (b'vary', b'Accept-Encoding'), (b'x-served-by', b'<romm-host>'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=7WNZa%2F399%2BVRFoNT0R%2ByibZ7Sb6F%2FyyKgM5ttINFIr0sxNE6JFVPVJ%2Bkl90vZ3kDiR56DenNqLgTZHGRO9KvUJe%2F6rhgpFddoKWfN5hleD9t3%2FNvoNp%2FR424xBEn3VGNR90vRtU8EXLmxmSMaxim"}]}'), (b'CF-RAY', b'a0d33342caf462b9-HAM'), (b'alt-svc', b'h3=":443"; ma=86400')])
2026-06-17 17:48:44,672 INFO httpx: HTTP Request: GET http://romm.batsnest.de/api/states?rom_id=266 "HTTP/1.1 200 OK"
2026-06-17 17:48:44,672 DEBUG httpcore.http11: receive_response_body.started request=<Request [b'GET']>
2026-06-17 17:48:44,672 DEBUG httpcore.http11: receive_response_body.complete
2026-06-17 17:48:44,672 DEBUG httpcore.http11: response_closed.started
2026-06-17 17:48:44,672 DEBUG httpcore.http11: response_closed.complete
2026-06-17 17:48:44,673 DEBUG httpcore.http11: send_request_headers.started request=<Request [b'GET']>
2026-06-17 17:48:44,673 DEBUG httpcore.http11: send_request_headers.complete
2026-06-17 17:48:44,673 DEBUG httpcore.http11: send_request_body.started request=<Request [b'GET']>
2026-06-17 17:48:44,673 DEBUG httpcore.http11: send_request_body.complete
2026-06-17 17:48:44,673 DEBUG httpcore.http11: receive_response_headers.started request=<Request [b'GET']>
2026-06-17 17:48:44,735 DEBUG httpcore.http11: receive_response_headers.complete return_value=(b'HTTP/1.1', 404, b'Not Found', [(b'Date', b'Wed, 17 Jun 2026 15:48:44 GMT'), (b'Content-Type', b'application/json'), (b'Content-Length', b'22'), (b'Connection', b'keep-alive'), (b'Server', b'cloudflare'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=NhcaYI2J7CzFe9hkMO1tZ0rzJn5iu1lkUShapx3FTBS1BB8rCRHOmX0bHPgCwCFzYqOPFpp2Rvq8VpiuW69WpJA53%2Fxnyxdd8ivrCiNKT6SEzfllzu60ykpQi8UtAO7XRLd9syAjOVNtzP9sgkS4"}]}'), (b'CF-RAY', b'a0d333434b7862b9-HAM'), (b'alt-svc', b'h3=":443"; ma=86400')])
2026-06-17 17:48:44,735 INFO httpx: HTTP Request: GET http://romm.batsnest.de/api/states/14/content "HTTP/1.1 404 Not Found"
2026-06-17 17:48:44,736 DEBUG httpcore.http11: receive_response_body.started request=<Request [b'GET']>
2026-06-17 17:48:44,736 DEBUG httpcore.http11: receive_response_body.complete
2026-06-17 17:48:44,736 DEBUG httpcore.http11: response_closed.started
2026-06-17 17:48:44,736 DEBUG httpcore.http11: response_closed.complete
RomM returned HTTP 404 Not Found."
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A per-file content 404 is reflected in the pull summary counts (e.g. failed/skipped) and surfaced to the user in CLI and GUI, not raised as an unhandled HTTPStatusError
- [x] #2 Non-404 HTTP errors and auth failures (401/403/5xx) on listing or content still abort/surface as errors — only per-file content 404 is tolerated, errors are not blanket-swallowed
- [x] #3 A test exercises a 404 content fetch occurring mid-batch and asserts the run continues and counts the skip; existing pull tests still pass
- [x] #4 Pulling a game whose RomM /api/saves or /api/states lists an entry whose /content endpoint returns 404 completes the run instead of aborting: the missing file is skipped+counted, all other saves/states for that game and remaining games still pull
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Wrap downloader() call in pull.py in per-file try/except for httpx.HTTPStatusError 404\n2. On 404: increment failed, call on_error, continue\n3. Non-404 HTTP errors still propagate\n4. Add test: 404 mid-batch continues run and counts failed
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fixed in pull.py: wrapped downloader() call in try/except httpx.HTTPStatusError; 404 increments failed+calls on_error+continues; non-404 re-raises. Two new tests. 454 tests pass. Committed a67332f.

Follow-up UX: orphan 404s split into separate 'missing' count (not 'failed'). Sonic Advance case = 2 saves already on disk (skipped) + 2 orphan state rows (404). Now shows 'Missing on RomM: 2' instead of scary 'Failed: 2'. CLI+GUI summaries updated. 454 tests pass. Committed 14b899b.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: AI triage
created: 2026-06-18 00:24
---
> *This was generated by AI during triage.*

## Agent Brief

**Category:** bug
**Summary:** A single orphan save/state whose RomM `/content` endpoint 404s aborts the entire pull.

**Current behavior:**
`pull` fetches saves then states for each game. For each listed remote file it calls the client's content-download method, which raises on any non-2xx (`raise_for_status`). The pull loop only guards the local *write* (catches OSError, "one unwritable file shouldn't abort the run"); it does not guard the *fetch*. RomM can list a state/save row in `/api/states` (or `/api/saves`) whose underlying content blob is gone, so `GET /api/{states,saves}/{id}/content` returns 404. That 404 propagates out of `pull_games`, the CLI maps any HTTPStatusError to "RomM returned HTTP 404 Not Found" and the whole pull dies — even though the real file was already retrieved through the other endpoint.

Confirmed repro (Sonic Advance, rom_id 266): `/api/saves/5/content` (.state) 200, `/api/saves/4/content` (.srm) 200, then `/api/states?rom_id=266` 200 lists state id 14, and `/api/states/14/content` → 404 → run aborts.

**Desired behavior:**
A per-file content fetch that 404s is treated like the existing unwritable-file case: skip that one file, record it in the summary counts, continue with the remaining files and games. The user sees a completed pull with a count of skipped/failed files rather than a hard error.

**Key interfaces:**
- The pull routine that iterates `(list_saves/download_save_content, list_states/download_state_content)` per game — the content-fetch call needs to be inside per-file error handling, mirroring the existing OSError-around-write tolerance.
- The pull summary dict (currently written/skipped/kept/failed) — the tolerated 404 should land in one of these counts and be reportable.
- CLI and GUI pull entry points — must not turn a tolerated per-file 404 into a fatal error.

**Acceptance criteria:** see the task's Acceptance Criteria list.

**Out of scope:**
- The secondary "API key has to be re-set after" symptom — split to its own task.
- Changing how/why RomM lists orphan state rows, or de-duplicating the `/api/saves` vs `/api/states` double-fetch (states pulled via legacy `/api/saves` routing). Behavioral fix only; don't redesign the dual-endpoint pull.
---
<!-- COMMENTS:END -->
