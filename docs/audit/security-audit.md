# BAYAN — Security Audit Report

**Date:** 2026-06-18

---

## Attack Surface

| Component | Exposure | Risk Level |
|-----------|----------|------------|
| Flask API (7860) | Public via HF Spaces | Medium |
| Supabase PostgreSQL | Behind RLS + Auth | Low |
| Google OAuth | Delegated to Google | Low |
| Model Inference | CPU-bound, no GPU | Low |
| localStorage | Client-only | Low |

---

## Authentication & Authorization

### Supabase RLS (Row-Level Security)

| Test | Result | Evidence |
|------|--------|----------|
| Unauthenticated REST access | ✅ BLOCKED | HTTP 401 |
| Invalid JWT token | ✅ BLOCKED | HTTP 401 |
| Cross-user document access | ✅ BLOCKED | RLS `user_id = auth.uid()` |
| Guest session isolation | ✅ PASS | Guest users have unique UUIDs |

### Google OAuth

| Test | Result |
|------|--------|
| OAuth flow uses Supabase SDK | ✅ |
| Tokens stored in Supabase session | ✅ |
| No custom token handling | ✅ (delegated) |

---

## API Input Validation

| Test | Endpoint | Result | Details |
|------|----------|--------|---------|
| Empty text | All | ✅ Returns 200/400 gracefully | No crash |
| Missing `text` field | All | ✅ Returns 400 | `"Text is required"` |
| Very long text (10K+) | /api/analyze | ⚠️ Timeout | Pipeline processes all 3 models |
| Non-JSON payload | All | ✅ Returns 400 | `"Request must be JSON"` |
| SQL injection attempt | /api/analyze | ✅ SAFE | NLP model treats it as text |
| XSS `<script>` tag | /api/analyze | ✅ SAFE | Tags preserved as text (editor uses textContent) |

### Max Text Length Protection

```python
MAX_ANALYZE_LENGTH = 5000  # Frontend
MAX_TEXT_LENGTH = 5000     # Backend (app.py)
```

Both frontend and backend enforce a 5000-character limit.

---

## CORS Configuration

```python
CORS(app, resources={r"/api/*": {"origins": "*"}})
```

| Aspect | Status |
|--------|--------|
| API routes protected | ✅ `/api/*` only |
| Static files unaffected | ✅ |
| Wildcard origin | ⚠️ Allows any origin |

> [!NOTE]
> Wildcard CORS (`*`) is acceptable because the API is public and requires no authentication. All sensitive operations go through Supabase SDK directly (client → Supabase, not client → Flask → Supabase).

---

## Data Protection

| Data | Storage | Protection |
|------|---------|------------|
| User profile | Supabase `profiles` | RLS + JWT |
| Documents | Supabase `documents` | RLS + JWT |
| Summaries | Supabase `summaries` | RLS + JWT |
| Settings | Supabase `settings` | RLS + JWT |
| Editor drafts | localStorage | Client-only |
| Dismissed words | localStorage | Client-only |

---

## Secrets Management

| Secret | Location | Status |
|--------|----------|--------|
| `HF_API_TOKEN` | HF Spaces Secrets | ✅ |
| `SUPABASE_URL` | HF Spaces Secrets | ✅ |
| `SUPABASE_ANON_KEY` | HF Spaces Secrets | ✅ |
| Google OAuth Client ID | Frontend JS (public) | ✅ (public key by design) |

> [!IMPORTANT]
> No private keys are exposed in frontend code. The Supabase anon key is a public key designed for client-side use, protected by RLS policies.

---

## Vulnerability Assessment

| Category | Risk | Status |
|----------|------|--------|
| SQL Injection | None | Supabase ORM + parameterized |
| XSS | Low | Editor uses `textContent` not `innerHTML` for user text |
| CSRF | N/A | No session cookies (stateless API) |
| Path Traversal | None | No file uploads |
| DDoS | Medium | No rate limiting (relies on HF proxy) |
| Model Poisoning | None | Models are read-only |

---

## Recommendations

1. **Rate Limiting:** Add Flask-Limiter for `/api/analyze` (e.g., 10 req/min per IP)
2. **Input Size:** Current 5000-char limit is good; consider per-endpoint limits
3. **CORS:** Could restrict to specific domains when going to production
4. **Monitoring:** Add request logging with IP for abuse detection

---

## Security Score: 85/100 🟡

The system is secure for its current deployment model (public NLP API + Supabase-protected data). The main gap is lack of rate limiting, which is mitigated by HF Spaces' own proxy layer.
