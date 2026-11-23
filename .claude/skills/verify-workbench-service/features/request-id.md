# Request identity

Every HTTP response the workbench serves carries an `X-Request-Id` header so a client, an operator and
the server log can talk about the same request.

## Sub-features

- `reqid-present` returns a non-empty `X-Request-Id` on responses the app handles itself.
- `reqid-unique` gives different requests different ids (12 hex characters from `uuid4`).
- `reqid-unknown-route` still sets the header on an unregistered `/api/v1/...` path, which returns `404`.

## How to get to it (user POV)

- Any HTTP client sends a request to the service base URL; the response headers carry `X-Request-Id`.
- Operators quote that value when reading server logs or filing an issue.

## Driving it with verifyctl

Preconditions:

- `verifyctl.sh doctor <run-id>` prints `OK`.

- **Header present.** `verifyctl.sh req <run-id> /api/v1/__verify_ready`. Expect `HTTP/1.1 404 Not Found`
  and a header line `x-request-id: <12 hex chars>`. (There are no product routes yet; the middleware
  runs before routing, so the header is still set.)
- **Ids differ.** Run the same command twice; expect two different `x-request-id` values.
- **Compare with the log.** `grep -c 'api/v1/__verify_ready' .verify/run/<run-id>/uvicorn.log` shows the
  request reached the server, so a missing header is not "the request never arrived".
- **Proof.** Save both full responses (status line, headers, body) to
  `.verify/evidence/<run-id>/request-id.txt`.

## Gotchas

- The header value is `uuid4().hex[:12]`, so it is 12 lowercase hex characters, not a UUID.
- The default FastAPI 404 body is `{"detail":"Not Found"}`; the `{code, message, details, requestId}`
  envelope only appears on routes that raise `ApiError` (`src/vigil_workbench/api/errors.py`), and no product
  route exists yet. Do not assert the envelope on an unregistered path.
- A `curl -I` HEAD request also gets the header; do not treat HEAD body differences as a defect.
