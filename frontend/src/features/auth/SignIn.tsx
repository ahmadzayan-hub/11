import { useState } from 'react'
import { Icon } from '../../shared/components/Icon'
import type { AuthConfig } from '../../shared/types'

interface SignInProps {
  config: AuthConfig
  onSignedIn: (token: string) => void
}

/** Sign-in against the deployment's managed identity provider.
 *
 *  Credentials go straight from the browser to the provider's own
 *  endpoint (Supabase Auth) using its publishable key; this application
 *  never receives, stores, or proxies a password. It only keeps the
 *  returned access token to authorize API calls. */
export function SignIn({ config, onSignedIn }: SignInProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const canUseProvider = config.flows.length > 0

  async function providerRequest(path: string, body: unknown) {
    const response = await fetch(`${config.provider_url}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        apikey: config.publishable_key,
        Authorization: `Bearer ${config.publishable_key}`,
      },
      body: JSON.stringify(body),
    })
    const payload = await response.json().catch(() => null)
    if (!response.ok) {
      const message =
        payload && typeof payload === 'object' && payload !== null
          ? ((payload as Record<string, unknown>).error_description ??
             (payload as Record<string, unknown>).msg ??
             (payload as Record<string, unknown>).message)
          : null
      throw new Error(typeof message === 'string' ? message : 'Sign-in failed.')
    }
    return payload as Record<string, unknown> | null
  }

  async function signInWithPassword(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const payload = await providerRequest('/auth/v1/token?grant_type=password', {
        email: email.trim(),
        password,
      })
      const token = payload?.access_token
      if (typeof token !== 'string' || !token) {
        throw new Error('The provider did not return an access token.')
      }
      setPassword('')
      onSignedIn(token)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Sign-in failed.')
    } finally {
      setBusy(false)
    }
  }

  async function sendMagicLink() {
    if (!email.trim()) {
      setError('Enter your email address first.')
      return
    }
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      await providerRequest('/auth/v1/otp', { email: email.trim() })
      setNotice(`Check ${email.trim()} for a sign-in link.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not send the link.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="signin" aria-label="Sign in">
      <div className="signin__card">
        <span className="brand__mark signin__mark" aria-hidden="true">
          A
        </span>
        <h1 className="signin__title">Sign in to Agentic OS</h1>
        <p className="signin__desc">
          This deployment requires an account. Your credentials go directly to the
          identity provider — Agentic OS never sees them.
        </p>

        {canUseProvider ? (
          <form onSubmit={signInWithPassword}>
            <div className="field">
              <label className="field__label" htmlFor="signin-email">
                Email
              </label>
              <input
                id="signin-email"
                className="field__input"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                disabled={busy}
                required
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="signin-password">
                Password
              </label>
              <input
                id="signin-password"
                className="field__input"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={busy}
              />
            </div>
            <div className="signin__actions">
              <button type="submit" className="btn btn--primary" disabled={busy || !email.trim()}>
                {busy ? <span className="spinner" aria-hidden="true" /> : null}
                Sign in
              </button>
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => void sendMagicLink()}
                disabled={busy}
              >
                Email me a link
              </button>
            </div>
          </form>
        ) : (
          <p className="signin__warning" role="status">
            <Icon name="alert" size={16} />
            This server requires authentication but no provider is configured for the
            browser. Set SUPABASE_URL and SUPABASE_ANON_KEY on the server.
          </p>
        )}

        <p
          className={`statusline ${error ? 'statusline--error' : notice ? 'statusline--success' : ''}`}
          role="status"
          aria-live="polite"
        >
          {error ?? notice ?? ''}
        </p>
      </div>
    </main>
  )
}
