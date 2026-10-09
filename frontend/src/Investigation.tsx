import { useEffect, useRef, useState } from 'react'

const api = (import.meta.env.VITE_API_BASE_URL || `${location.protocol}//${location.hostname}:8000`).replace(/\/$/, '')
type Result = {
  id: string; created_at: string; method: string; summary: string
  observations: { text: string; event_ids: string[]; representative?: { endpoint: string; message: string; stack_trace: string; received_at: string } }[]
  hypotheses: { cause: string; supporting_event_ids: string[] }[]
  suggested_checks: string[]; limitations: string[]
}

export default function Investigation({ project, incident, onExpired, onEvent }: {
  project: string; incident: string; onExpired: () => void; onEvent: (id: string) => void
}) {
  const [result, setResult] = useState<Result | null>(null)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const request = useRef<AbortController | null>(null)
  const expired = useRef(onExpired)
  expired.current = onExpired

  async function load(refresh = false) {
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setBusy(true); setError('')
    try {
      const response = await fetch(`${api}/api/v1/projects/${project}/incidents/${incident}/${refresh ? 'investigate' : 'investigation'}`, {
        method: refresh ? 'POST' : 'GET', credentials: 'include', cache: 'no-store', signal: controller.signal,
      })
      if (response.status === 401) { expired.current(); throw new Error('Your session ended. Please sign in again.') }
      const body = await response.json()
      if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Unable to load investigation.')
      if (!controller.signal.aborted) setResult(refresh ? body : body.investigation)
    } catch (e) {
      if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Unable to load investigation.')
    } finally { if (!controller.signal.aborted) setBusy(false) }
  }
  useEffect(() => {
    setResult(null); void load()
    return () => request.current?.abort()
  }, [project, incident])

  const citations = (ids: string[]) => <details><summary>Inspect {ids.length} cited event{ids.length === 1 ? '' : 's'}</summary>
    <div className="investigation-citations">{ids.map(id => <button className="text-button" key={id} onClick={() => onEvent(id)}>{id}</button>)}</div>
  </details>
  return <section className="investigation" aria-label="Rule-based investigation" aria-busy={busy}>
    <h3>Rule-based investigation</h3>
    <p>A saved review of bounded evidence. Candidate causes are hypotheses, not confirmed diagnoses.</p>
    <button className="text-button" disabled={busy} onClick={() => void load(true)}>{result ? 'Refresh investigation' : 'Run investigation'}</button>
    {busy && <p role="status">Loading investigation…</p>}
    {error && <p className="auth-error" role="alert">{error} <button onClick={() => void load()}>Retry saved result</button></p>}
    {!busy && !error && !result && <p>No saved investigation yet.</p>}
    {result && <>
      <p>Saved {new Date(result.created_at).toISOString()} · Method: {result.method}</p>
      <p>{result.summary}</p>
      <h4>Observations</h4>
      {!result.observations.length && <p>No observations supported by retained evidence.</p>}
      {result.observations.map((o, i) => <article className="incident-group" key={i}>
        <p>{o.text}</p>{o.representative && <details><summary>Representative stored excerpt</summary>
          <p>{o.representative.received_at} · {o.representative.endpoint || 'Endpoint unavailable'}</p>
          <p>{o.representative.message}</p><pre>{o.representative.stack_trace || 'Stack trace unavailable'}</pre>
        </details>}{citations(o.event_ids)}
      </article>)}
      <h4>Candidate causes · unverified</h4>
      {!result.hypotheses.length && <p>Insufficient evidence to propose a cause.</p>}
      {result.hypotheses.map((h, i) => <article className="incident-group" key={i}><p>{h.cause}</p>{citations(h.supporting_event_ids)}</article>)}
      <h4>Suggested checks</h4><ul>{result.suggested_checks.map(s => <li key={s}>{s}</li>)}</ul>
      <h4>Limitations</h4><ul>{result.limitations.map(s => <li key={s}>{s}</li>)}</ul>
    </>}
  </section>
}
