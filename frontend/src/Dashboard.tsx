import { useEffect, useRef, useState, type FormEvent } from 'react'
import IncidentDetails from './IncidentDetails'
import { EventDetail } from './Events'
import './dashboard.css'

const api = (import.meta.env.VITE_API_BASE_URL || `${location.protocol}//${location.hostname}:8000`).replace(/\/$/, '')
const utc = (value: string | null) => value ? new Date(value).toISOString().replace('T', ' ').replace('Z', ' UTC') : '—'
type Project = { id: string; name: string }
type Incident = { id: string; service: string; status: string; severity: string; started_at: string; last_seen_at: string; resolved_at: string | null; request_count: number; failure_count: number }
type Bucket = { start_time: string; end_time: string; requests: number; failures: number }
type Overview = { requests: number; failures: number; total_events: number; error_rate: number | null; median_latency_ms: number | null; active_incidents: number; start_time: string; end_time: string; generated_at: string; buckets: Bucket[]; total_services: number; services_truncated: boolean; services: { service: string; requests: number; failures: number; events: number; active_incident: boolean; last_evaluated_at: string | null; evaluation_status: string | null }[] }
type Recent = { event_id: string; message: string; received_at: string; service: string; level: string }

async function read(path: string, signal: AbortSignal, expired: () => void) {
  const response = await fetch(`${api}/api/v1/projects${path}`, { credentials: 'include', cache: 'no-store', signal })
  if (signal.aborted) throw new Error('Cancelled')
  if (response.status === 401) { expired(); throw new Error('Your session ended. Please sign in again.') }
  const data = await response.json()
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Check your filters and try again.')
  return data
}

export default function Dashboard({ mode, onExpired, onProjects }: { mode: 'Overview' | 'Incidents'; onExpired: () => void; onProjects: () => void }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [project, setProject] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [reload, setReload] = useState(0)
  const expired = useRef(onExpired); expired.current = onExpired
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError('')
    read('', controller.signal, () => expired.current()).then(data => {
      if (!controller.signal.aborted) { setProjects(data.projects); setProject(current => data.projects.some((p: Project) => p.id === current) ? current : data.projects[0]?.id || '') }
    }).catch(e => { if (!controller.signal.aborted) setError(e.message || 'Unable to load projects.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [reload])
  return <div className="dashboard">
    <div className="event-project"><label>Project<select aria-label="Dashboard project" disabled={loading} value={project} onChange={e => setProject(e.target.value)}>
      {!projects.length && <option value="">No projects</option>}{projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
    </select></label><button className="outline" disabled={loading} onClick={() => setReload(n => n + 1)}>Refresh projects</button></div>
    {error && <p className="auth-error" role="alert">{error} <button onClick={() => setReload(n => n + 1)}>Retry projects</button></p>}
    {loading ? <p role="status">Loading projects…</p> : !error && (project ? mode === 'Overview' ? <ProjectOverview key={project} project={project} onExpired={onExpired}/> : <IncidentList key={project} project={project} onExpired={onExpired}/> : <section className="panel empty"><h2>No projects yet</h2><p>Create a project to start collecting events.</p><button className="text-button" onClick={onProjects}>Open Projects & Keys</button></section>)}
  </div>
}

function ProjectOverview({ project, onExpired }: { project: string; onExpired: () => void }) {
  const [hours, setHours] = useState('1')
  const [service, setService] = useState('')
  const [draft, setDraft] = useState('')
  const [data, setData] = useState<Overview | null>(null)
  const [recent, setRecent] = useState<Recent[]>([])
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const expired = useRef(onExpired); expired.current = onExpired
  useEffect(() => {
    const controller = new AbortController()
    const end = new Date(), start = new Date(end.getTime() - Number(hours) * 3600000)
    const params = new URLSearchParams({ start_time: start.toISOString(), end_time: end.toISOString() })
    if (service) params.set('service', service)
    setData(null); setRecent([]); setError(''); setSelected(null)
    Promise.all([read(`/${project}/overview?${params}`, controller.signal, () => expired.current()), read(`/${project}/events?${params}&limit=10`, controller.signal, () => expired.current())])
      .then(([overview, events]) => { if (!controller.signal.aborted) { setData(overview); setRecent(events.events) } })
      .catch(e => { if (!controller.signal.aborted) setError(e.message || 'Unable to load overview.') })
    return () => controller.abort()
  }, [project, hours, service, reload])
  const max = Math.max(1, ...data?.buckets.map(b => b.requests) || [])
  return <>
    <form className="event-filters dashboard-filters" onSubmit={e => { e.preventDefault(); setService(draft.trim()); setReload(n => n + 1) }}>
      <label>Received-time window<select value={hours} onChange={e => setHours(e.target.value)}><option value="1">Last hour</option><option value="24">Last 24 hours</option><option value="168">Last 7 days</option></select></label>
      <label>Service<input value={draft} maxLength={255} placeholder="All services (exact name to filter)" onChange={e => setDraft(e.target.value)}/></label>
      <button className="primary">Apply / refresh overview</button>
    </form>
    {error ? <p className="auth-error" role="alert">{error} <button onClick={() => setReload(n => n + 1)}>Retry overview</button></p> : !data ? <p role="status">Loading overview…</p> : <>
      <p className="dashboard-time">Received from {utc(data.start_time)} to {utc(data.end_time)} (end excluded). Updated {utc(data.generated_at)}.</p>
      <div className="stats">{[
        ['Requests', data.requests.toLocaleString(), `${data.total_events} total events`],
        ['Failure rate', data.error_rate === null ? '—' : `${(data.error_rate * 100).toFixed(1)}%`, `${data.failures} failed requests`],
        ['Active incidents', data.active_incidents.toLocaleString(), 'Current stored status · all time'],
        ['Median latency', data.median_latency_ms === null ? '—' : `${data.median_latency_ms.toFixed(1)} ms`, 'Requests with recorded latency'],
      ].map(([label, value, note]) => <section className="stat" key={label}><h2>{label}</h2><div className="stat-value">{value}</div><p>{note}</p></section>)}</div>
      {!data.total_events && <p className="empty">No events in this window. Try a longer window or send traffic.</p>}
      <section className="panel dashboard-panel"><h2>Request activity</h2><p>Mint: all requests · Coral: failures included within requests. Exception-only events do not count as requests.</p>
        <div className="dashboard-chart" role="img" aria-label={`24 time buckets: ${data.requests} requests, ${data.failures} failures. Exact counts available below.`}>{data.buckets.map(b => <div key={b.start_time} title={`${utc(b.start_time)}: ${b.requests} requests, ${b.failures} failures`} style={{ height: `${b.requests / max * 100}%` }}><span style={{ height: `${b.requests ? b.failures / b.requests * 100 : 0}%` }}/></div>)}</div>
        <details><summary>View exact chart counts</summary><div className="table-scroll"><table><thead><tr><th>Bucket start (UTC)</th><th>Requests</th><th>Failures</th></tr></thead><tbody>{data.buckets.map(b => <tr key={b.start_time}><td>{utc(b.start_time)}</td><td>{b.requests}</td><td>{b.failures}</td></tr>)}</tbody></table></div></details>
      </section>
      <section className="panel dashboard-panel"><h2>Services in this window</h2><p>Detector state is the last stored evaluation, not a live health guarantee. Check its timestamp; a stopped worker leaves the state unchanged.</p>
        <div className="table-scroll"><table><thead><tr><th>Service</th><th>Requests</th><th>Failures</th><th>Active incident</th><th>Last detector state</th><th>Evaluated (UTC)</th></tr></thead><tbody>{data.services.map(s => <tr key={s.service}><td>{s.service}</td><td>{s.requests}</td><td>{s.failures}</td><td>{s.active_incident ? 'Yes' : 'No'}</td><td>{s.evaluation_status?.replaceAll('_', ' ') || 'Not evaluated'}</td><td>{utc(s.last_evaluated_at)}</td></tr>)}</tbody></table></div>
        {!data.services.length && <p>No services in this window.</p>}{data.services_truncated && <p>Showing 100 of {data.total_services} services. Filter by an exact service name to inspect another.</p>}
      </section>
      <section className="panel dashboard-panel"><h2>Recent stored events</h2><p>Up to 10 newest events in the selected window.</p>{recent.map(event => <button className="incident-evidence" key={event.event_id} onClick={() => setSelected(event.event_id)}><span>{event.level} · {event.service} · {event.message}</span><small>{utc(event.received_at)} · Inspect event →</small></button>)}{!recent.length && <p>No events to show.</p>}</section>
    </>}
    {selected && <EventDetail project={project} id={selected} onExpired={onExpired} onClose={() => setSelected(null)}/>}
  </>
}

const blank = { status: '', service: '', start: '', end: '' }
function IncidentList({ project, onExpired }: { project: string; onExpired: () => void }) {
  const [draft, setDraft] = useState(blank), [filters, setFilters] = useState(blank)
  const [cursors, setCursors] = useState(['']), [next, setNext] = useState<string | null>(null)
  const [rows, setRows] = useState<Incident[]>([]), [error, setError] = useState(''), [validation, setValidation] = useState('')
  const [loading, setLoading] = useState(true), [reload, setReload] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const expired = useRef(onExpired); expired.current = onExpired
  const cursor = cursors[cursors.length - 1]
  useEffect(() => {
    const controller = new AbortController(), params = new URLSearchParams({ limit: '25' })
    if (cursor) params.set('cursor', cursor)
    if (filters.status) params.set('status', filters.status)
    if (filters.service) params.set('service', filters.service)
    if (filters.start) params.set('start_time', new Date(filters.start + 'Z').toISOString())
    if (filters.end) params.set('end_time', new Date(filters.end + 'Z').toISOString())
    setLoading(true); setRows([]); setError(''); setNext(null)
    read(`/${project}/incidents?${params}`, controller.signal, () => expired.current()).then(data => { if (!controller.signal.aborted) { setRows(data.incidents); setNext(data.next_cursor) } })
      .catch(e => { if (!controller.signal.aborted) setError(e.message || 'Unable to load incidents.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [project, filters, cursor, reload])
  function apply(e: FormEvent) {
    e.preventDefault()
    if ([draft.start, draft.end].some(v => v && !Number.isFinite(Date.parse(v + 'Z'))) || (draft.start && draft.end && draft.start >= draft.end)) { setValidation('Enter a valid UTC range with the start before the end.'); return }
    setValidation(''); setFilters({ ...draft, service: draft.service.trim() }); setCursors(['']); setReload(n => n + 1)
  }
  const back = useRef<HTMLButtonElement>(null)
  useEffect(() => { if (selected) back.current?.focus() }, [selected])
  return <>
    {selected && <><button ref={back} className="outline dashboard-back" onClick={() => { const id = selected; setSelected(null); requestAnimationFrame(() => document.getElementById(`incident-${id}`)?.focus()) }}>← Back to incidents</button><IncidentDetails key={selected} project={project} id={selected} onExpired={onExpired}/></>}
    <section className="panel dashboard-panel" hidden={!!selected}>
      <h2>Stored incidents</h2><p>Newest first by first failure time. Status is recorded by the detector; refresh to load changes.</p>
      <form className="event-filters dashboard-filters" onSubmit={apply}>
        <label>Status<select value={draft.status} onChange={e => setDraft({ ...draft, status: e.target.value })}><option value="">All statuses</option><option value="active">Active</option><option value="resolved">Resolved</option></select></label>
        <label>Service<input value={draft.service} maxLength={255} placeholder="Exact service name" onChange={e => setDraft({ ...draft, service: e.target.value })}/></label>
        <label>Started from (UTC)<input type="datetime-local" value={draft.start} onChange={e => setDraft({ ...draft, start: e.target.value })}/></label>
        <label>Started before (UTC)<input type="datetime-local" value={draft.end} onChange={e => setDraft({ ...draft, end: e.target.value })}/></label>
        <button className="primary">Apply filters</button><button className="outline" type="button" onClick={() => { setDraft(blank); setFilters(blank); setValidation(''); setCursors(['']); setReload(n => n + 1) }}>Clear filters</button>
      </form>
      <button className="text-button" disabled={loading} onClick={() => { setCursors(['']); setReload(n => n + 1) }}>Refresh incidents</button>
      {validation && <p className="auth-error" role="alert">{validation}</p>}
      {error && <p className="auth-error" role="alert">{error} <button onClick={() => setReload(n => n + 1)}>Retry incidents</button></p>}
      {loading ? <p role="status">Loading incidents…</p> : !error && <div className="table-scroll"><table><thead><tr><th>Service / severity</th><th>Status</th><th>First failure (UTC)</th><th>Last failure (UTC)</th><th>Resolved (UTC)</th><th>Latest window failures / requests</th><th>Details</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td>{row.service} · {row.severity}</td><td><span className={`badge ${row.status === 'active' ? 'ERROR' : 'INFO'}`}>{row.status}</span></td><td>{utc(row.started_at)}</td><td>{utc(row.last_seen_at)}</td><td>{utc(row.resolved_at)}</td><td>{row.failure_count} / {row.request_count}</td><td><button id={`incident-${row.id}`} className="text-button" aria-label={`Inspect incident ${row.id}`} onClick={() => setSelected(row.id)}>Inspect</button></td></tr>)}</tbody></table>{!rows.length && <p className="empty">No incidents match these filters. Incidents appear after the running detector confirms sustained failures.</p>}</div>}
      <div className="table-footer event-pagination"><span>Page {cursors.length} · {rows.length} incidents</span><div><button className="outline" disabled={loading || cursors.length === 1} onClick={() => setCursors(c => c.slice(0, -1))}>Previous</button><button className="outline" disabled={loading || !!error || !next} onClick={() => { if (next) setCursors(c => [...c, next]) }}>Next</button></div></div>
    </section>
  </>
}
