# MYOB Auth

Online MYOB files use OAuth. The server requests consent, captures the authorization code and `businessId`, exchanges the code for tokens, and encrypts tokens on disk.

One MYOB Developer App key/secret can be reused across many client files, but OAuth consent is per business/company file. Repeat the authorization flow once for every business the accountant needs to work with.

For hosted manual callbacks, deploy the static helper in `site/` and keep the MYOB Developer Dashboard redirect URI identical to the MCP `redirect_uri`. The deployment and accountant workflow are documented in [callback-site.md](callback-site.md).

Important behavior:

- `prompt=consent` is included.
- New SME scopes are configured by default.
- `businessId` from the callback is persisted as company context.
- Tokens are stored in an encrypted multi-business registry.
- access tokens refresh automatically.
- manual code exchange is available when the localhost callback fails.

Tools:

```text
myob_oauth_authorize_business
myob_oauth_authorize
myob_oauth_exchange_redirect_url
myob_oauth_exchange_code
myob_oauth_refresh
myob_oauth_logout
myob_auth_status
myob_company_get_context
myob_business_list_authorized
myob_business_set_default
myob_business_remove_authorization
```
