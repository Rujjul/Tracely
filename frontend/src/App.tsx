import { useEffect, useState } from 'react'
import { Activity, ArrowDownLeft, ArrowRight, Check, ChevronDown, CircleHelp, Command, Database, ExternalLink, FileText, LayoutDashboard, Radio, Search, Settings2, ShieldCheck, TriangleAlert, X, Zap } from 'lucide-react'

import Projects from './Projects'

type Page = 'Overview' | 'Events' | 'Incidents' | 'Setup' | 'Projects'
const api = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const events = [
  { id: 'evt-001', time: '14:32:51', level: 'ERROR', service: 'payment-api', message: 'Database connection timed out', endpoint: 'POST /payments', latency: 2431 },
  { id: 'evt-002', time: '14:32:48', level: 'ERROR', service: 'payment-api', message: 'Database connection timed out', endpoint: 'POST /payments', latency: 2408 },
  { id: 'evt-003', time: '14:32:45', level: 'INFO', service: 'gateway', message: 'Request completed successfully', endpoint: 'GET /health', latency: 24 },
  { id: 'evt-004', time: '14:32:42', level: 'WARN', service: 'inventory-api', message: 'Dependency response slower than expected', endpoint: 'GET /stock', latency: 842 },
  { id: 'evt-005', time: '14:32:39', level: 'INFO', service: 'gateway', message: 'Request completed successfully', endpoint: 'GET /products', latency: 38 },
  { id: 'evt-006', time: '14:32:36', level: 'ERROR', service: 'payment-api', message: 'Unhandled exception in payment handler', endpoint: 'POST /payments', latency: 156 },
]
const bars = [22,30,24,36,28,32,25,39,33,27,40,35,31,44,36,32,42,30,37,43,35,46,41,34,48,40,52,43,37,50,46,42,57,48,54,67,74,81,76,88,83,71,78,66,61,54,48,42]

export default function App({ onExpired }: { onExpired: () => void }) {
  const [page, setPage] = useState<Page>('Overview')
  const [health, setHealth] = useState<'checking' | 'online' | 'offline'>('checking')
  const [query, setQuery] = useState('')
  const [level, setLevel] = useState('ALL')
  const [selected, setSelected] = useState<typeof events[number] | null>(null)
  const [incident, setIncident] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    async function check() {
      try {
        const response = await fetch(`${api}/api/v1/health`, { signal: controller.signal })
        const body = await response.json()
        if (!controller.signal.aborted) setHealth(response.ok && body.status === 'ok' ? 'online' : 'offline')
      } catch { if (!controller.signal.aborted) setHealth('offline') }
    }
    void check()
    const interval = window.setInterval(check, 15000)
    return () => { controller.abort(); window.clearInterval(interval) }
  }, [])
  useEffect(() => {
    const close = (e: KeyboardEvent) => { if (e.key === 'Escape') { setSelected(null); setIncident(false) } }
    window.addEventListener('keydown', close)
    return () => window.removeEventListener('keydown', close)
  }, [])
  const filtered = events.filter(e => (level === 'ALL' || e.level === level) && `${e.message} ${e.service} ${e.endpoint}`.toLowerCase().includes(query.toLowerCase()))
  const nav = (name: Page) => { setPage(name); setQuery(''); setLevel('ALL') }
  return <div className="app">
    <aside className="sidebar">
      <a className="brand" href="#" onClick={e => { e.preventDefault(); nav('Overview') }}><span className="brand-icon"><Activity size={22}/></span>tracely<span className="brand-dot">.</span></a>
      <div className="workspace"><span className="workspace-icon">D</span><div><strong>Demo workspace</strong><small>Local environment</small></div><ChevronDown size={14}/></div>
      <div className="nav-label">WORKSPACE</div>
      <nav>{([['Projects', Database], ['Overview', LayoutDashboard], ['Events', FileText], ['Incidents', TriangleAlert], ['Setup', Settings2]] as const).map(([name, Icon]) => <button key={name} className={page === name ? 'nav-item active' : 'nav-item'} onClick={() => nav(name)}><Icon size={18}/>{name}{name === 'Incidents' && <span className="nav-count">1</span>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="local-card"><ShieldCheck size={20}/><strong>Local by design</strong><p>Your investigation starts here.<br/>Your data stays with you.</p></div><button className="help" onClick={() => nav('Setup')}><CircleHelp size={17}/> Getting started <ArrowRight size={15}/></button><div className="profile"><span>DE</span><div><strong>Demo environment</strong><small>Frontend preview · v0.1</small></div></div></div>
    </aside>
    <main>
      <header><div className="breadcrumb">Workspace <span>/</span> <strong>{page}</strong></div><div className={`api-status ${health}`}><i/>{health === 'online' ? 'API connected' : health === 'checking' ? 'Checking API' : 'API offline'}</div></header>
      <div className="content">
        <div className="page-heading"><div><div className="eyebrow">YOUR SYSTEM, IN FOCUS</div><h1>{page === 'Projects' ? 'Projects & keys' : page === 'Overview' ? 'Workspace overview' : page === 'Events' ? 'Event explorer' : page === 'Incidents' ? 'Incidents' : 'Get started with Tracely'}</h1><p>{page === 'Projects' ? 'Manage your applications and their ingestion keys.' : page === 'Overview' ? 'A clearer picture of what happened. A faster path to why.' : page === 'Events' ? 'Follow the evidence, one event at a time.' : page === 'Incidents' ? 'Understand failures and the signals behind them.' : 'A small foundation for better incident investigations.'}</p></div><span className="environment"><span/> Local demo</span></div>
        <div className="preview-banner"><Zap size={16}/><span><strong>Preview workspace.</strong> Charts, events, and incidents use sample data. Projects, accounts, and API health are live.</span><button onClick={() => nav('Setup')}>View setup <ArrowRight size={14}/></button></div>
        {page === 'Projects' && <Projects onExpired={onExpired}/>}
        {page === 'Overview' && <>
          <div className="section-heading"><h2>At a glance</h2><span className="muted">Sample window · 14:00–14:35 UTC</span></div>
          <div className="stats">{[{label:'Requests',value:'2,846',icon:Activity,note:'Across 3 services',color:'purple'},{label:'Error rate',value:'12.4%',icon:TriangleAlert,note:'Above the 10% demo threshold',color:'red'},{label:'Active incidents',value:'1',icon:Radio,note:'payment-api needs attention',color:'orange'},{label:'Median latency',value:'142',unit:'ms',icon:Zap,note:'Request processing time',color:'blue'}].map(s=><div className="stat" key={s.label}><div className="stat-label">{s.label}<s.icon size={17} className={s.color}/></div><div className="stat-value">{s.value}<small>{s.unit}</small></div><div className="stat-note">{s.note}</div></div>)}</div>
          <div className="charts"><section className="panel traffic"><div className="panel-title"><div><h2>Request activity</h2><p>Traffic and failures over the sample window</p></div><div className="legend"><span><i/>Requests</span><span><i/>Errors</span></div></div><div className="chart" role="img" aria-label="Illustrative request traffic with an error spike near 14:25 UTC"><div className="axis"><span>100</span><span>75</span><span>50</span><span>25</span><span>0</span></div><div className="plot"><div className="gridlines"><i/><i/><i/><i/><i/></div><div className="bars">{bars.map((height,i)=><div className="bar" key={i} style={{height:`${height}%`}}><span style={{height:`${i>33 ? 25+(i%4)*5 : i%7===0 ? 8 : 0}%`}}/></div>)}</div><div className="time-axis"><span>14:00</span><span>14:10</span><span>14:20</span><span>14:30</span></div></div></div></section>
          <section className="panel services"><div className="panel-title"><div><h2>Services</h2><p>3 services in this preview</p></div><Database size={18}/></div>{[{name:'payment-api',rate:'28.1% errors',state:'Degraded',bad:true},{name:'gateway',rate:'0.0% errors',state:'Healthy',bad:false},{name:'inventory-api',rate:'0.0% errors',state:'Healthy',bad:false}].map(s=><div className="service" key={s.name}><span className={`service-icon ${s.bad?'bad':''}`}><Command size={17}/></span><div><strong>{s.name}</strong><small>{s.rate}</small></div><span className={`service-state ${s.bad?'bad':''}`}><i/>{s.state}</span></div>)}<div className="service-foot"><ShieldCheck size={14}/> Sample service health</div></section></div>
          <section className="incident-strip"><span className="incident-icon"><TriangleAlert size={21}/></span><div><div className="incident-title"><strong>Elevated error rate in payment-api</strong><span className="badge ERROR">Active</span></div><p>Repeated database timeouts · First observed at 14:25 UTC · Sample incident</p></div><button className="outline" onClick={()=>setIncident(true)}>Inspect incident <ArrowRight size={15}/></button></section>
        </>}
        {(page === 'Overview' || page === 'Events') && <section className="panel event-panel"><div className="panel-title"><div><h2>{page==='Overview'?'Recent events':'All sample events'}</h2><p>The latest signals from your services</p></div>{page==='Overview' && <button className="text-button" onClick={()=>nav('Events')}>View all events <ArrowRight size={15}/></button>}</div><div className="filters"><label className="search"><Search size={17}/><input aria-label="Search events" placeholder="Search messages, services, or endpoints…" value={query} onChange={e=>setQuery(e.target.value)}/></label><select aria-label="Filter by level" value={level} onChange={e=>setLevel(e.target.value)}><option value="ALL">All levels</option><option>ERROR</option><option>WARN</option><option>INFO</option></select><span>{filtered.length} events</span></div><div className="table-scroll"><table><thead><tr><th>TIME (UTC)</th><th>LEVEL</th><th>SERVICE</th><th>MESSAGE</th><th>LATENCY</th><th><span className="sr-only">Details</span></th></tr></thead><tbody>{filtered.map(e=><tr key={e.id}><td className="mono muted">{e.time}</td><td><span className={`badge ${e.level}`}>{e.level}</span></td><td className="mono">{e.service}</td><td>{e.message}</td><td className="mono muted">{e.latency.toLocaleString()} ms</td><td><button className="icon-button" aria-label={`Inspect event ${e.id}`} onClick={()=>setSelected(e)}><ArrowDownLeft size={16}/></button></td></tr>)}</tbody></table>{!filtered.length && <div className="empty">No events match your filters.<button className="text-button" onClick={()=>{setQuery('');setLevel('ALL')}}>Clear filters</button></div>}</div><div className="table-footer"><span>Showing {filtered.length} sample events</span><span>All timestamps in UTC</span></div></section>}
        {page==='Incidents' && <section className="panel"><div className="panel-title"><div><h2>Active incidents <span className="count">1</span></h2><p>Sample data · detection is not implemented yet</p></div></div><button className="incident-row" onClick={()=>setIncident(true)}><TriangleAlert className="orange"/><div><strong>Elevated error rate in payment-api</strong><p>Database timeouts · 14:25 UTC · INC-001</p></div><span className="badge ERROR">Active</span><ArrowRight size={18}/></button></section>}
        {page==='Setup' && <div className="setup-grid"><section className="panel setup"><h2>Your local foundation</h2><p>The frontend is ready to explore. Start the Python API to connect the health indicator.</p><h3>1. Start the backend</h3><pre>cd backend{'\n'}py -m venv .venv{'\n'}.venv\Scripts\python -m pip install -r requirements.txt{'\n'}.venv\Scripts\python -m uvicorn app.main:app --reload</pre><h3>2. Start the frontend</h3><pre>cd frontend{'\n'}npm install{'\n'}npm run dev</pre><a className="primary" href={`${api}/docs`} target="_blank" rel="noreferrer">Open API documentation <ExternalLink size={15}/></a></section><section className="panel setup"><h2>What’s connected</h2><ul className="checklist"><li><Check/>React + TypeScript + Vite</li><li><Check/>FastAPI health endpoint</li><li><Check/>Searchable sample event explorer</li><li><Check/>Responsive incident workspace</li></ul><h3>Coming in later phases</h3><p>Stored events, detection, and investigations.</p><div className="setup-note">PostgreSQL is available through Docker Compose. Preview data is not stored.</div></section></div>}
        <footer><span><Activity size={14}/> Tracely · Make sense of the signals.</span><span>Local-first investigation workspace</span></footer>
      </div>
    </main>
    {(selected || incident) && <div className="modal-backdrop" onClick={()=>{setSelected(null);setIncident(false)}}><section className="modal" role="dialog" aria-modal="true" aria-label={selected?'Sample event details':'Sample incident details'} onClick={e=>e.stopPropagation()}><button autoFocus className="close icon-button" aria-label="Close details" onClick={()=>{setSelected(null);setIncident(false)}}><X size={20}/></button><div className="eyebrow">SAMPLE EVIDENCE</div><h2>{selected?'Event details':'Elevated error rate'}</h2><p>{selected?selected.message:'Repeated database timeout errors in payment-api.'}</p><dl>{Object.entries(selected || {incident:'INC-001',service:'payment-api',status:'Active',started_at:'14:25 UTC',observation:'Several sample requests failed with database timeouts.',limitation:'Sample illustration only. No detector or investigation has run.'}).map(([key,value])=><div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{value}</dd></div>)}</dl><div className="setup-note">This is preview data. Live ingestion and evidence-linked investigations arrive in later phases.</div></section></div>}
  </div>
}
