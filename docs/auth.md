# MYOB Auth

Online MYOB files use OAuth. The server requests consent, captures the authorization code and `businessId`, exchanges the code for tokens, and encrypts tokens on disk.

Important behavior:

- `prompt=consent` is included.
- New SME scopes are configured by default.
- `businessId` from the callback is persisted as company context.
- access tokens refresh automatically.
- manual code exchange is available when the localhost callback fails.

Tools:

```text
myob_oauth_authorize
myob_oauth_exchange_code
myob_oauth_refresh
myob_oauth_logout
myob_auth_status
myob_company_get_context
```
