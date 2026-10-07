import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ArrowRight, RefreshCw, X } from 'lucide-react'
import './events.css'

const api = (import.meta.env.VITE_API_BASE_URL || `${location.protocol}//${location.hostname}:8000`).replace(/\/$/, '')
type Project = { id: string; name: string }
type Event = { id: string; event_id: string; timestamp: string; received_at: string; event_type: string; level: string; service: string; message: string; endpoint: string | null; status_code: number | null; latency_ms: number | null; exception_type: string | null; stack_trace?: string | null; metadata?: Record<string, unknown> | null; fingerprint?: string | null }
type Filters = { service: string; level: string; q: string; start: string; end: string }
const blank: Filters = { service: '', level: '', q: '', start: '', end: '' }
const utc = (value: string) => new Date(value).toISOString().replace('T', ' ').replace('Z', ' UTC')

async function read(path: string, signal: AbortSignal, expired: () => void) {
  const response = await fetch(`${api}/api/v1/projects${path}`, { credentials: 'include', cache: 'no-store', signal })
  if (signal.aborted) throw new Error('Request cancelled')
  if (response.status === 401) { expired(); throw new Error('Your session ended. Please sign in again.') }
  const data = await response.json()
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Check your filters and try again.')
  return data
}

export default function Events({ onExpired, onProjects }: { onExpired: () => void; onProjects: () => void }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [project, setProject] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)
  const expired = useRef(onExpired)
  expired.current = onExpired
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError('')
    read('', controller.signal, () => expired.current()).then(data => {
      if (controller.signal.aborted) return
      setProjects(data.projects)
      setProject(current => data.projects.some((item: Project) => item.id === current) ? current : data.projects[0]?.id || '')
    }).catch(e => { if (!controller.signal.aborted) setError(e.message || 'Unable to load projects.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [reload])
  return <div className="live-events">
    <div className="event-project"><label>Project<select aria-label="Event project" value={project} disabled={loading || !projects.length} onChange={e => setProject(e.target.value)}>
      {!projects.length && <option value="">No projects</option>}{projects.map(item => <option key={item.id} value={item.id}>{item.name} · {item.id.slice(0, 8)}</option>)}
    </select></label><button className="outline" disabled={loading} onClick={() => setReload(n => n + 1)}>Refresh projects</button></div>
    {error && <div className="auth-error" role="alert">{error} <button onClick={() => setReload(n => n + 1)}>Retry</button></div>}
    {loading ? <p className="empty" role="status">Loading projects…</p> : !error && (!project ? <section className="panel empty"><h2>No projects yet</h2><p>Create a project and send events with its ingestion key.</p><button className="text-button" onClick={onProjects}>Open Projects & Keys <ArrowRight size={15}/></button></section> : <EventList key={project} project={project} onExpired={() => expired.current()}/>)}
  </div>
}

function EventList({ project, onExpired }: { project: string; onExpired: () => void }) {
  const [draft, setDraft] = useState<Filters>(blank)
  const [filters, setFilters] = useState<Filters>(blank)
  const [cursors, setCursors] = useState<string[]>([''])
  const [limit, setLimit] = useState('50')
  const [rows, setRows] = useState<Event[]>([])
  const [next, setNext] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filterError, setFilterError] = useState('')
  const [reload, setReload] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const expired = useRef(onExpired)
  expired.current = onExpired
  const cursor = cursors[cursors.length - 1]
  useEffect(() => {
    const controller = new AbortController()
    const params = new URLSearchParams({ limit })
    if (cursor) params.set('cursor', cursor)
    if (filters.q) params.set('q', filters.q)
    if (filters.service) params.set('service', filters.service)
    if (filters.level) params.set('level', filters.level)
    if (filters.start) params.set('start_time', new Date(filters.start + 'Z').toISOString())
    if (filters.end) params.set('end_time', new Date(filters.end + 'Z').toISOString())
    setLoading(true); setRows([]); setNext(null); setError(''); setSelected(null)
    read(`/${project}/events?${params}`, controller.signal, () => expired.current()).then(data => {
      if (!controller.signal.aborted) { setRows(data.events); setNext(data.next_cursor) }
    }).catch(e => { if (!controller.signal.aborted) setError(e.message || 'Unable to load events.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [project, filters, cursor, limit, reload])
  function apply(event: FormEvent) {
    event.preventDefault()
    if ([draft.start, draft.end].some(value => value && !Number.isFinite(Date.parse(value + 'Z')))) { setFilterError('Enter a valid UTC date and time.'); return }
    if (draft.start && draft.end && draft.start >= draft.end) { setFilterError('Start time must be earlier than end time.'); return }
    setFilterError(''); setFilters({ ...draft, q: draft.q.trim(), service: draft.service.trim() }); setCursors(['']); setReload(n => n + 1)
  }
  function clear() { setDraft(blank); setFilters(blank); setFilterError(''); setCursors(['']); setReload(n => n + 1) }
  return <section className="panel event-panel">
    <div className="panel-title"><div><h2>Stored events</h2><p>Newest received first · Time filters use received time in UTC</p></div><button className="text-button" disabled={loading} onClick={() => { setCursors(['']); setReload(n => n + 1) }}><RefreshCw size={14}/>Refresh events</button></div>
    <form className="event-filters" onSubmit={apply}>
      <label>Search<input placeholder="Message, service, endpoint, exception…" value={draft.q} maxLength={200} onChange={e => setDraft({ ...draft, q: e.target.value })}/></label>
      <label>Service<input placeholder="Exact service name" maxLength={255} value={draft.service} onChange={e => setDraft({ ...draft, service: e.target.value })}/></label>
      <label>Level<select aria-label="Level" value={draft.level} onChange={e => setDraft({ ...draft, level: e.target.value })}><option value="">All levels</option>{['TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL', 'FATAL'].map(item => <option key={item}>{item}</option>)}</select></label>
      <label>Received from (UTC)<input type="datetime-local" value={draft.start} onChange={e => setDraft({ ...draft, start: e.target.value })}/></label>
      <label>Received before (UTC)<input type="datetime-local" value={draft.end} onChange={e => setDraft({ ...draft, end: e.target.value })}/></label>
      <div className="event-filter-actions"><button className="primary" type="submit">Apply filters</button><button className="outline" type="button" onClick={clear}>Clear filters</button></div>
    </form>
    {filterError && <p className="auth-error" role="alert">{filterError}</p>}
    {error && <p className="auth-error" role="alert">{error} <button onClick={() => setReload(n => n + 1)}>Retry events</button></p>}
    {loading ? <p className="empty" role="status">Loading events…</p> : !error && <div className="table-scroll"><table><thead><tr><th>RECEIVED (UTC)</th><th>LEVEL</th><th>SERVICE</th><th>MESSAGE</th><th>STATUS / LATENCY</th><th>DETAILS</th></tr></thead><tbody>{rows.map(item => <tr key={item.id}>
      <td className="mono muted">{utc(item.received_at)}</td><td><span className={`badge ${item.level}`}>{item.level}</span></td><td className="mono">{item.service}</td><td className="event-message">{item.message}</td><td className="mono muted">{item.status_code ?? '—'} / {item.latency_ms === null ? '—' : `${item.latency_ms.toLocaleString()} ms`}</td><td><button className="text-button" aria-label={`Inspect event ${item.event_id}`} onClick={() => setSelected(item.event_id)}>Inspect</button></td>
    </tr>)}</tbody></table>{!rows.length && <div className="empty"><h3>No events found</h3><p>Try clearing filters, or send events using this project’s ingestion key and refresh.</p><button className="text-button" onClick={clear}>Clear filters</button></div>}</div>}
    <div className="table-footer event-pagination"><label>Per page <select aria-label="Events per page" value={limit} onChange={e => { setLimit(e.target.value); setCursors(['']) }}>{['25', '50', '100'].map(size => <option key={size}>{size}</option>)}</select></label><span>Page {cursors.length} · {rows.length} events</span><div><button className="outline" disabled={loading || cursors.length === 1} onClick={() => setCursors(current => current.slice(0, -1))}>Previous</button><button className="outline" disabled={loading || !!error || !next} onClick={() => { if (next) setCursors(current => [...current, next]) }}>Next</button></div></div>
    {selected && <EventDetail project={project} id={selected} onClose={() => setSelected(null)} onExpired={onExpired}/>}
  </section>
}

export function EventDetail({ project, id, onClose, onExpired }: { project: string; id: string; onClose: () => void; onExpired: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const expired = useRef(onExpired)
  expired.current = onExpired
  const [event, setEvent] = useState<Event | null>(null)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => { const element = dialog.current; element?.showModal(); return () => element?.close() }, [])
  useEffect(() => {
    const controller = new AbortController()
    setError(''); setEvent(null)
    read(`/${project}/events/${id}`, controller.signal, () => expired.current()).then(data => { if (!controller.signal.aborted) setEvent(data.event) })
      .catch(e => { if (!controller.signal.aborted) setError(e.message || 'Unable to load event details.') })
    return () => controller.abort()
  }, [project, id, retry])
  return <dialog className="event-detail" ref={dialog} aria-labelledby="stored-event-title" onCancel={onClose} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
    <div><button autoFocus className="close icon-button" aria-label="Close event details" onClick={onClose}><X size={20}/></button><div className="eyebrow">STORED EVIDENCE</div><h2 id="stored-event-title">Event details</h2>
      {error ? <p className="auth-error" role="alert">{error} <button onClick={() => setRetry(n => n + 1)}>Retry details</button></p> : !event ? <p role="status">Loading event details…</p> : <>
        <p className="event-detail-message">{event.message}</p><dl>{Object.entries({ 'Event ID': event.event_id, 'Request time (UTC)': utc(event.timestamp), 'Received (UTC)': utc(event.received_at), Type: event.event_type, Level: event.level, Service: event.service, Endpoint: event.endpoint, Status: event.status_code, 'Latency (ms)': event.latency_ms, Exception: event.exception_type, Fingerprint: event.fingerprint || 'Not grouped' }).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value ?? '—'}</dd></div>)}</dl>
        <h3>Stack trace</h3><pre>{event.stack_trace || 'No stack trace recorded.'}</pre><h3>Metadata</h3><pre>{event.metadata ? JSON.stringify(event.metadata, null, 2) : 'No metadata recorded.'}</pre>
      </>}
    </div>
  </dialog>
}
