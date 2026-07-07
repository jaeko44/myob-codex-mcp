# Static MYOB Callback Site

The `site/` folder contains a static callback page for `https://app.professionalaccounting.com.au`.

It is intentionally dependency-free:

- no build step;
- no analytics;
- no network calls;
- no API key or client secret fields;
- no local storage or cookies.

The page only reads the current browser URL, extracts the MYOB OAuth query parameters, and prepares copy-ready text for Codex:

- a Codex instruction for `myob_oauth_exchange_redirect_url`;
- the full redirect URL;
- a JSON payload;
- a compact MCP tool-call reference.

## Deployment

Any static host works as long as the final URL exactly matches the redirect URI registered in MYOB and configured in the local MCP config.

Recommended low-friction options:

1. GitHub Pages from the `site/` folder.
2. Azure Static Web Apps.
3. Azure Storage static website hosting.
4. Cloudflare Pages.

For GitHub Pages, the repository includes `.github/workflows/pages.yml` to deploy the `site/` folder from `main`. It also includes `site/CNAME`:

```text
app.professionalaccounting.com.au
```

Point DNS for `app.professionalaccounting.com.au` to the selected static host, then make sure HTTPS is active before using it as a MYOB redirect URI.

For this repo's GitHub Pages deployment, add this DNS record:

```text
Type:  CNAME
Name:  app
Value: jaeko44.github.io
```

After DNS resolves, GitHub can issue the certificate and HTTPS enforcement can be enabled for the Pages site.

## MYOB Configuration

Keep these values aligned:

```toml
[myob]
redirect_uri = "https://app.professionalaccounting.com.au"
```

MYOB Developer Dashboard:

```text
Redirect Uri: https://app.professionalaccounting.com.au
```

If you decide to use a path such as `/callback`, update both MYOB and the MCP config to the same value:

```text
https://app.professionalaccounting.com.au/callback
```

The included `site/404.html` redirects unknown static paths back to the root handler while preserving the query string. This helps static hosts handle `/callback?code=...` routes.

## Accountant Workflow

1. In Codex, call `myob_oauth_authorize_business`.
2. Sign in to MYOB as an admin user.
3. Select the business/company file to authorize.
4. After MYOB redirects to the static page, click `Copy Instruction`.
5. Paste the instruction into Codex.
6. Codex calls `myob_oauth_exchange_redirect_url`.
7. The MCP stores encrypted tokens for that `businessId`.

Repeat the authorization flow once for every MYOB business/company file that should be available through the MCP.

## Consent Model

One MYOB Developer App key/secret can be reused across client businesses, but OAuth consent is still granted per selected MYOB business/company file. Adding a `businessId` to config is not enough by itself. The MCP needs an encrypted refresh token that was issued for that business.

After a business has been authorized and its refresh token is stored, accountants using that same token registry do not need to re-consent for routine reads or approved writes. The token can still stop working if MYOB revokes access, the authorizing user loses access, scopes change, or the token store is moved without its encryption key.

For local installs, each computer has its own token store by default:

- safest default: each accountant/admin consents once per business on their own machine;
- centralized option: build an admin onboarding/token-broker flow that stores tokens centrally or exports/imports encrypted per-business authorizations with audit controls.

Do not distribute raw refresh tokens in chat or source control.
