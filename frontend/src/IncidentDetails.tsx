import { useEffect, useRef, useState, type FormEvent } from 'react'
import { EventDetail } from './Events'
import './incidents.css'

const api = (import.meta.env.VITE_API_BASE_URL || `${location.protocol}//${location.hostname}:8000`).replace(/\/$/, '')
const utc = (value: string | null) => value ? new Date(value).toISOString().replace('T', ' ').replace('Z', ' UTC') : '—'
type Details = {
  incident: { id: string; service: string; status: string; severity: string; incident_type: string; started_at: string; last_seen_at: string; resolved_at: string | null; request_count: number; failure_count: number; detector_version: string; thresholds: Record<string, number> }
  evidence: { total_events: number; ungrouped_events: number; total_groups: number; events_truncated: boolean; groups_truncated: boolean; limitations: string[]; groups: { fingerprint: string; exception_type: string; event_count: number; first_seen_at: string; last_seen_at: string }[]; events: { event_id: string; message: string; received_at: string; fingerprint: string | null }[] }
}

export default function IncidentDetails({ onExpired }: { onExpired: () => void }) {
  const [projects, setProjects] = useState<{ id: string; name: string }[]>([])
  const [project, setProject] = useState('')
  const [id, setId] = useState('')
  const [data, setData] = useState<Details | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [retry, setRetry] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const pending = useRef<AbortController | null>(null)
  const expired = useRef(onExpired)
  expired.current = onExpired
  async function read(path: string, signal: AbortSignal) {
    const response = await fetch(`${api}/api/v1/projects${path}`, { credentials: 'include', cache: 'no-store', signal })
    if (response.status === 401) { expired.current(); throw new Error('Your session ended. Please sign in again.') }
    const body = await response.json()
    if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Check the incident ID and try again.')
    return body
  }
  useEffect(() => {
    const controller = new AbortController()
    setError(''); setLoading(true)
    read('', controller.signal).then(body => {
      if (!controller.signal.aborted) { setProjects(body.projects); setProject(body.projects[0]?.id || '') }
    }).catch(e => { if (!controller.signal.aborted) setError(e.message || 'Unable to load projects.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => { controller.abort(); pending.current?.abort() }
  }, [retry])
  function clear() { pending.current?.abort(); setData(null); setError(''); setSelected(null); setLoading(false) }
  async function inspect(event: FormEvent) {
    event.preventDefault()
    clear()
    const controller = new AbortController()
    pending.current = controller
    setLoading(true)
    try {
      const result = await read(`/${project}/incidents/${encodeURIComponent(id.trim())}`, controller.signal)
      if (!controller.signal.aborted) setData(result)
    } catch (e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Unable to load incident.') }
    finally { if (!controller.signal.aborted) setLoading(false) }
  }
  return <section className="panel incident-details">
    <h2>Stored incident details</h2>
    <p>Choose a project and enter a stored incident UUID. The browsable incident dashboard arrives in Phase 9.</p>
    <form className="event-filters" onSubmit={inspect}>
      <label>Project<select required value={project} onChange={e => { clear(); setProject(e.target.value) }}>
        {!projects.length && <option value="">No projects available</option>}{projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
      </select></label>
      <label>Incident ID<input required maxLength={36} placeholder="Incident UUID" value={id} onChange={e => { clear(); setId(e.target.value) }}/></label>
      <button className="primary" disabled={loading || !project} type="submit">Inspect incident</button>
    </form>
    {!projects.length && !loading && <button className="outline" onClick={() => setRetry(n => n + 1)}>Refresh projects</button>}
    {loading && <p role="status">Loading…</p>}
    {error && <p className="auth-error" role="alert">{error}</p>}
    {data && <>
      <h3>{data.incident.service} · {data.incident.status}</h3>
      <dl className="incident-facts">{Object.entries({ 'Incident ID': data.incident.id, Type: data.incident.incident_type, Severity: data.incident.severity, 'First failure': utc(data.incident.started_at), 'Last failure': utc(data.incident.last_seen_at), Resolved: utc(data.incident.resolved_at), 'Latest window requests': data.incident.request_count, 'Latest window failures': data.incident.failure_count, Detector: data.incident.detector_version }).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
      <details><summary>Recorded detector thresholds</summary><pre>{JSON.stringify(data.incident.thresholds, null, 2)}</pre></details>
      <h3>Exception groups</h3><p>{data.evidence.total_events} correlated events · {data.evidence.total_groups} groups · {data.evidence.ungrouped_events} ungrouped</p>
      {!data.evidence.groups.length && <p>No grouped exception evidence in this interval.</p>}
      {data.evidence.groups.map(group => <article className="incident-group" key={group.fingerprint}><strong>{group.exception_type}</strong><p>{group.event_count} events · {utc(group.first_seen_at)} – {utc(group.last_seen_at)}</p><code>{group.fingerprint}</code></article>)}
      {data.evidence.groups_truncated && <p>Showing the 20 largest groups.</p>}
      <h3>Correlated events</h3><p>Newest first. Open an event to inspect its stack trace and fingerprint.</p>
      {!data.evidence.events.length && <p>No retained event evidence in this interval.</p>}
      {data.evidence.events.map(event => <button className="incident-evidence" key={event.event_id} onClick={() => setSelected(event.event_id)}><span>{event.message}</span><small>{utc(event.received_at)} · {event.event_id}</small><span>Inspect event →</span></button>)}
      {data.evidence.events_truncated && <p>Showing the latest 50 events. Use the Events page to browse more in this service and time interval.</p>}
      <h3>Evidence limitations</h3><ul>{data.evidence.limitations.map(text => <li key={text}>{text}</li>)}</ul>
    </>}
    {selected && <EventDetail project={project} id={selected} onExpired={onExpired} onClose={() => setSelected(null)}/>}
  </section>
}
