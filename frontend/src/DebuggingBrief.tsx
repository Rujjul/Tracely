import { useEffect, useRef, useState } from 'react'
import './guided-demo.css'

const api = (import.meta.env.VITE_API_BASE_URL || `${location.protocol}//${location.hostname}:8000`).replace(/\/$/, '')
export default function DebuggingBrief({ project, incident, demoText, onExpired }: {
  project?: string; incident?: string; demoText?: string; onExpired?: () => void
}) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const area = useRef<HTMLTextAreaElement>(null)
  const expired = useRef(onExpired)
  expired.current = onExpired
  useEffect(() => {
    setText(''); setStatus(''); setError('')
    if (!open) return
    if (demoText) { setText(demoText); setLoading(false); return }
    const controller = new AbortController()
    setLoading(true)
    fetch(`${api}/api/v1/projects/${project}/incidents/${incident}/debugging-brief`, {
      credentials: 'include', cache: 'no-store', signal: controller.signal,
    }).then(async r => {
      if (r.status === 401) { expired.current?.(); throw new Error('Your session ended. Please sign in again.') }
      const body = await r.json()
      if (!r.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Unable to prepare brief.')
      if (!controller.signal.aborted) setText(body.text)
    }).catch(e => { if (!controller.signal.aborted) setError(e.message || 'Unable to prepare brief.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [open, project, incident, demoText])
  async function copy() {
    try { await navigator.clipboard.writeText(text); setStatus('Copied. You choose where to paste it.') }
    catch { setStatus('Automatic copy unavailable. Select the text below and use Ctrl+C or Command+C.'); area.current?.focus(); area.current?.select() }
  }
  return <section className="debugging-brief">
    <button className="text-button" aria-expanded={open} onClick={() => setOpen(v => !v)}>{open ? 'Close brief preview' : 'Copy debugging brief'}</button>
    {open && <div>
      <h3>Preview before sharing{demoText ? ' · Synthetic demo' : ''}</h3>
      <p>Review for sensitive information. Copying does not send anything to an AI or change your code.</p>
      {loading && <p role="status">Preparing brief…</p>}
      {error && <p role="alert">{error} Close and reopen the preview to retry.</p>}
      {text && <><label>Debugging brief<textarea ref={area} readOnly value={text} rows={14}/></label>
        <button className="text-button" onClick={() => void copy()}>Copy reviewed brief</button>
        <button className="text-button" onClick={() => { area.current?.focus(); area.current?.select(); setStatus('Text selected. Use Ctrl+C or Command+C, or your device copy menu.') }}>Select text for manual copy</button>
      </>}
      <p role="status">{status}</p>
    </div>}
  </section>
}
