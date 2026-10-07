import { useEffect, useState } from 'react'
import { Activity, ArrowRight, Check, ChevronDown, CircleHelp, Database, ExternalLink, FileText, LayoutDashboard, Settings2, ShieldCheck, TriangleAlert } from 'lucide-react'

import Projects from './Projects'
import Events from './Events'
import Dashboard from './Dashboard'

type Page = 'Overview' | 'Events' | 'Incidents' | 'Setup' | 'Projects'
const api = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
export default function App({ onExpired }: { onExpired: () => void }) {
  const [page, setPage] = useState<Page>('Overview')
  const [health, setHealth] = useState<'checking' | 'online' | 'offline'>('checking')
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
  const nav = (name: Page) => setPage(name)
  return <div className="app">
    <aside className="sidebar">
      <a className="brand" href="#" onClick={e => { e.preventDefault(); nav('Overview') }}><span className="brand-icon"><Activity size={22}/></span>tracely<span className="brand-dot">.</span></a>
      <div className="workspace"><span className="workspace-icon">D</span><div><strong>Demo workspace</strong><small>Local environment</small></div><ChevronDown size={14}/></div>
      <div className="nav-label">WORKSPACE</div>
      <nav>{([['Projects', Database], ['Overview', LayoutDashboard], ['Events', FileText], ['Incidents', TriangleAlert], ['Setup', Settings2]] as const).map(([name, Icon]) => <button key={name} className={page === name ? 'nav-item active' : 'nav-item'} onClick={() => nav(name)}><Icon size={18}/>{name}</button>)}</nav>
      <div className="sidebar-bottom"><div className="local-card"><ShieldCheck size={20}/><strong>Local by design</strong><p>Your investigation starts here.<br/>Your data stays with you.</p></div><button className="help" onClick={() => nav('Setup')}><CircleHelp size={17}/> Getting started <ArrowRight size={15}/></button><div className="profile"><span>DE</span><div><strong>Demo environment</strong><small>Local workspace · v0.1</small></div></div></div>
    </aside>
    <main>
      <header><div className="breadcrumb">Workspace <span>/</span> <strong>{page}</strong></div><div className={`api-status ${health}`}><i/>{health === 'online' ? 'API connected' : health === 'checking' ? 'Checking API' : 'API offline'}</div></header>
      <div className="content">
        <div className="page-heading"><div><div className="eyebrow">YOUR SYSTEM, IN FOCUS</div><h1>{page === 'Projects' ? 'Projects & keys' : page === 'Overview' ? 'Workspace overview' : page === 'Events' ? 'Event explorer' : page === 'Incidents' ? 'Incidents' : 'Get started with Tracely'}</h1><p>{page === 'Projects' ? 'Manage your applications and their ingestion keys.' : page === 'Overview' ? 'A clearer picture of what happened. A faster path to why.' : page === 'Events' ? 'Follow the evidence, one event at a time.' : page === 'Incidents' ? 'Understand failures and the signals behind them.' : 'A small foundation for better incident investigations.'}</p></div><span className="environment"><span/> Local demo</span></div>
        {page === 'Projects' && <Projects onExpired={onExpired}/>}
        {page === 'Events' && <Events onExpired={onExpired} onProjects={() => nav('Projects')}/>}
        {(page === 'Overview' || page === 'Incidents') && <Dashboard mode={page} onExpired={onExpired} onProjects={() => nav('Projects')}/>}
        {page==='Setup' && <div className="setup-grid"><section className="panel setup"><h2>Your local foundation</h2><p>The frontend is ready to explore. Start the Python API to connect the health indicator.</p><h3>1. Start the backend</h3><pre>cd backend{'\n'}py -m venv .venv{'\n'}.venv\Scripts\python -m pip install -r requirements.txt{'\n'}.venv\Scripts\python -m uvicorn app.main:app --reload</pre><h3>2. Start the frontend</h3><pre>cd frontend{'\n'}npm install{'\n'}npm run dev</pre><a className="primary" href={`${api}/docs`} target="_blank" rel="noreferrer">Open API documentation <ExternalLink size={15}/></a></section><section className="panel setup"><h2>What’s connected</h2><ul className="checklist"><li><Check/>React + TypeScript + Vite</li><li><Check/>FastAPI health endpoint</li><li><Check/>Live project event explorer</li><li><Check/>Stored overview and incident dashboard</li></ul><h3>Coming in later phases</h3><p>Evidence-based investigations.</p><div className="setup-note">PostgreSQL is available through Docker Compose. Dashboard values come from stored project data.</div></section></div>}
        <footer><span><Activity size={14}/> Tracely · Make sense of the signals.</span><span>Local-first investigation workspace</span></footer>
      </div>
    </main>

  </div>
}
