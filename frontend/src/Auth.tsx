import { useEffect, useState, type FormEvent } from 'react'
import { Activity, ArrowRight, Check, Eye, EyeOff, ShieldCheck } from 'lucide-react'
import App from './App'
import './auth.css'

const api = (import.meta.env.VITE_API_BASE_URL || `${location.protocol}//${location.hostname}:8000`).replace(/\/$/, '')
type Session = { user: { id: string; email: string }; expires_at: string }
type Mode = 'login' | 'register' | 'link' | 'forgot' | 'reset'
async function request(path: string, body?: unknown) {
  const response = await fetch(`${api}/api/v1/auth/${path}`, {
    method: body === undefined ? 'GET' : 'POST', credentials: 'include',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Please check your email and password.')
  return data
}

export default function Auth() {
  const incoming = new URLSearchParams(location.search).get('auth')
  const [resetToken, setResetToken] = useState(() => new URLSearchParams(location.hash.slice(1)).get('reset_token') || '')
  const [mode, setMode] = useState<Mode>(location.hash.startsWith('#reset_token=') ? 'reset' : incoming === 'link' ? 'link' : 'login')
  const [session, setSession] = useState<Session | null>(null)
  const [checking, setChecking] = useState(true)
  const [google, setGoogle] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [visible, setVisible] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(incoming === 'google_error' ? 'Google sign-in was cancelled or could not be verified. Please try again.' : '')
  useEffect(() => {
    if (incoming && incoming !== 'link') history.replaceState(null, '', location.pathname)
    let active = true
    request('config').then(data => { if (active) setGoogle(data.google_enabled) }).catch(() => {})
    request('me').then(data => { if (active && incoming !== 'link' && mode !== 'reset') setSession(data) }).catch(() => {}).finally(() => { if (active) setChecking(false) })
    return () => { active = false }
  }, [])
  useEffect(() => {
    if (!session) return
    const expires = Date.parse(session.expires_at)
    const expire = () => { setSession(null); setMode('login'); setPassword(''); setError('Your 30-minute session ended. Please sign in again.') }
    const timer = window.setTimeout(expire, Math.max(0, expires - Date.now()))
    const check = () => { if (Date.now() >= expires) expire() }
    window.addEventListener('focus', check)
    return () => { clearTimeout(timer); window.removeEventListener('focus', check) }
  }, [session])
  function changeMode(next: Mode) { history.replaceState(null, '', location.pathname); setResetToken(''); setMode(next); setError(''); setPassword(''); setConfirmation('') }
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (mode === 'register' && password !== confirmation) { setError('Passwords do not match.'); return }
    setBusy(true); setError('')
    try {
      const data = await request(mode === 'link' ? 'google/link' : mode, mode === 'link' ? { password } : { email: email.trim(), password })
      history.replaceState(null, '', location.pathname)
      setSession(data); setPassword(''); setConfirmation('')
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to connect. Please try again.') }
    finally { setBusy(false) }
  }
  async function signOut() {
    setBusy(true)
    try { await request('logout', {}); setSession(null); setError(''); setMode('login') }
    catch { setError('Could not sign out. Check your connection and try again.') }
    finally { setBusy(false) }
  }
  if (checking) return <div className="auth-loading" role="status">Opening Tracely…</div>
  if (mode === 'forgot' || mode === 'reset') return <PasswordRecovery key={mode} token={resetToken} resetting={mode === 'reset'} onBack={() => changeMode('login')} onNewLink={() => changeMode('forgot')}/>
  if (session) return <><div className="account-bar"><span>Signed in as <strong>{session.user.email}</strong></span><button disabled={busy} onClick={signOut}>Sign out</button>{error && <span role="alert">{error}</span>}</div><App onExpired={() => { setSession(null); setMode('login'); setError('Your session ended. Please sign in again.') }} /></>
  return <div className="auth-shell">
    <section className="auth-story"><a className="auth-brand" href="/" aria-label="Tracely home"><span><Activity size={25}/></span>tracely.</a><div className="auth-story-body"><div className="auth-kicker">FOLLOW THE SIGNAL.</div><h1>Every incident<br/>has a story.<br/><em>Find yours.</em></h1><p>Bring the evidence together. Understand what happened. Get back to building.</p><div className="auth-signal" aria-hidden="true"><div><span/><span/><span/></div><svg viewBox="0 0 420 110"><path d="M0 65H80L97 50 110 78 128 25 145 90 161 48 177 65H245L264 50 281 78 300 35 320 65H420"/></svg><span className="signal-caption">FROM NOISE TO UNDERSTANDING</span></div><ul><li><Check size={15}/> Evidence, not guesswork</li><li><Check size={15}/> Local-first by design</li><li><Check size={15}/> Your systems, in focus</li></ul></div><span className="auth-copyright">Tracely · A clearer path to why.</span></section>
    <section className="auth-form-area"><div className="auth-topline"><ShieldCheck size={15}/> Your investigation starts here</div><div className="auth-card"><div className="auth-tabs" aria-label="Account access"><button className={mode!=='register'?'selected':''} onClick={()=>changeMode('login')}>Sign in</button><button className={mode==='register'?'selected':''} onClick={()=>changeMode('register')}>Sign up</button></div><h2>{mode==='register'?'Create your account':mode==='link'?'Confirm it’s you':'Welcome back'}</h2><p className="auth-subtitle">{mode==='register'?'A little less noise. A lot more clarity.':mode==='link'?'This Google email matches an existing account. Enter its password to securely link Google.':'Sign in to your Tracely workspace.'}</p>
      {mode!=='link' && <><button className="google-button" disabled={!google || busy} onClick={()=>{location.href=`${api}/api/v1/auth/google/start`}}><span className="google-g">G</span>Continue with Google</button>{!google && <p className="google-note">Google sign-in is awaiting setup. Email and password are available.</p>}<div className="auth-divider"><span/>{mode==='register'?'or sign up with email':'or use your email'}<span/></div></>}
      <form onSubmit={submit}>
        {mode!=='link' && <label className="auth-label">Email address<input type="email" autoComplete="email" placeholder="you@example.com" value={email} onChange={e=>setEmail(e.target.value)} maxLength={254} required disabled={busy}/></label>}
        <label className="auth-label">{mode==='link'?'Existing account password':'Password'}<div className="password-input"><input type={visible?'text':'password'} autoComplete={mode==='register'?'new-password':'current-password'} placeholder={mode==='register'?'Create a strong password':'Enter your password'} value={password} onChange={e=>setPassword(e.target.value)} minLength={mode==='register'?12:1} maxLength={128} required disabled={busy}/><button type="button" aria-label={visible?'Hide password':'Show password'} onClick={()=>setVisible(!visible)}>{visible?<EyeOff size={17}/>:<Eye size={17}/>}</button></div></label>
        {mode==='register' && <><p className="password-hint">Use 12–128 characters. Spaces and passphrases are welcome.</p><label className="auth-label">Confirm password<input type={visible?'text':'password'} autoComplete="new-password" placeholder="Re-enter your password" value={confirmation} onChange={e=>setConfirmation(e.target.value)} minLength={12} maxLength={128} required disabled={busy}/></label></>}
        {error && <div className="auth-error" role="alert">{error}</div>}
        {(mode === 'login' || mode === 'link') && <button className="auth-recovery-link" type="button" disabled={busy} onClick={() => changeMode('forgot')}>Forgot password?</button>}
        <button className="auth-submit" disabled={busy}>{busy?'Please wait…':mode==='register'?'Create account':mode==='link'?'Verify and link Google':'Sign in'}<ArrowRight size={17}/></button>
      </form><div className="auth-session"><ShieldCheck size={14}/> Your session expires 30 minutes after sign-in.</div><p className="auth-switch">{mode==='register'?'Already have an account?':'New to Tracely?'} <button onClick={()=>changeMode(mode==='register'?'login':'register')}>{mode==='register'?'Sign in':'Create an account'}</button></p></div><div className="auth-footnote">Investigate with context. Build with confidence.</div></section>
  </div>
}

function PasswordRecovery({ token, resetting, onBack, onNewLink }: { token: string; resetting: boolean; onBack: () => void; onNewLink: () => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (resetting && password !== confirmation) { setError('Passwords do not match.'); return }
    setBusy(true); setError(''); setMessage('')
    try {
      const data = await request(resetting ? 'reset-password' : 'forgot-password', resetting ? { token, password } : { email: email.trim() })
      setMessage(data.message)
      setDone(true)
      if (resetting) { history.replaceState(null, '', location.pathname); setPassword(''); setConfirmation('') }
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to connect. Please try again.') }
    finally { setBusy(false) }
  }
  return <main className="auth-form-area auth-recovery"><div className="auth-card">
    <a className="auth-brand" href="/">tracely.</a>
    <h2>{resetting ? 'Set a new password' : 'Forgot your password?'}</h2>
    <p className="auth-subtitle">{resetting ? 'Choose a new password with 12–128 characters.' : 'Enter your account email and we’ll send a link to reset your password. The link expires in 15 minutes.'}</p>
    {!done && <form onSubmit={submit}>
      {resetting ? <>
        <label className="auth-label">New password<input type="password" autoComplete="new-password" minLength={12} maxLength={128} required disabled={busy} value={password} onChange={e => setPassword(e.target.value)}/></label>
        <label className="auth-label">Confirm new password<input type="password" autoComplete="new-password" minLength={12} maxLength={128} required disabled={busy} value={confirmation} onChange={e => setConfirmation(e.target.value)}/></label>
      </> : <label className="auth-label">Email address<input type="email" autoComplete="email" maxLength={254} required disabled={busy} value={email} onChange={e => setEmail(e.target.value)}/></label>}
      {error && <div className="auth-error" role="alert">{error}</div>}
      <button className="auth-submit" disabled={busy}>{busy ? 'Please wait…' : resetting ? 'Reset password' : 'Send reset link'}<ArrowRight size={17}/></button>
    </form>}
    {message && <p className="auth-notice" role="status">{message}</p>}
    {!resetting && done && <p className="auth-subtitle">Check your spam folder too. If nothing arrives, wait a minute before trying again.</p>}
    {resetting && !done && <button className="auth-recovery-link" disabled={busy} onClick={onNewLink}>Request a new reset link</button>}
    {!resetting && done && <button className="auth-recovery-link" onClick={() => { setDone(false); setMessage('') }}>Try again</button>}
    <p className="auth-switch"><button disabled={busy} onClick={onBack}>Back to sign in</button></p>
  </div></main>
}
