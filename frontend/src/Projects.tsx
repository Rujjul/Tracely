import { useEffect, useState, type FormEvent } from 'react'
import { FolderPlus, KeyRound, Copy, Check, RefreshCw } from 'lucide-react'
import './projects.css'

const api = (import.meta.env.VITE_API_BASE_URL || `${location.protocol}//${location.hostname}:8000`).replace(/\/$/, '')
type Project = { id: string; name: string; created_at: string; key_prefix: string | null; key_created_at: string | null }
type Reveal = { name: string; value: string }

export default function Projects({ onExpired }: { onExpired: () => void }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [reveal, setReveal] = useState<Reveal | null>(null)
  const [rotate, setRotate] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  async function request(path = '', body?: unknown) {
    const response = await fetch(`${api}/api/v1/projects${path}`, {
      method: body === undefined ? 'GET' : 'POST', credentials: 'include', cache: 'no-store',
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    if (response.status === 401) { onExpired(); throw new Error('Your session ended. Please sign in again.') }
    const data = await response.json()
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Use a project name between 1 and 100 characters.')
    return data
  }
  async function load() {
    setLoading(true)
    try { setProjects((await request()).projects) }
    catch (e) { setError(e instanceof Error ? e.message : 'Unable to load projects.') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [])
  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const data = await request('', { name: name.trim() })
      setReveal({ name: data.project.name, value: data.ingestion_key }); setCopied(false); setName('')
      await load()
    } catch (e) { setError(e instanceof Error ? e.message : 'Creation failed. Refresh the project list before retrying.') }
    finally { setBusy(false) }
  }
  async function rotateKey(id: string) {
    setBusy(true); setError('')
    try {
      const data = await request(`/${id}/keys/rotate`, {})
      setReveal({ name: data.project.name, value: data.ingestion_key }); setCopied(false); setRotate(null)
      await load()
    } catch (e) { setError(e instanceof Error ? e.message : 'Rotation failed. Refresh before retrying.') }
    finally { setBusy(false) }
  }
  return <div className="projects-page">
    <div className="setup-note">Projects and keys are live. Event collection arrives in Phase 4; the overview and logs still use sample data.</div>
    {error && <div className="auth-error" role="alert">{error} <button onClick={()=>{setError('');void load()}} disabled={busy}>Retry loading</button></div>}
    {reveal && <section className="key-reveal" aria-label="New ingestion key"><div className="project-title"><KeyRound size={21}/><h2>Save your key for {reveal.name}</h2></div><p>This is the only time this key is shown. Save it somewhere secure before leaving this page. If lost, rotate it to create a replacement.</p><div className="key-value"><code data-testid="ingestion-key">{reveal.value}</code><button className="outline" onClick={async()=>{try { await navigator.clipboard.writeText(reveal.value);setCopied(true) } catch { setError('Clipboard unavailable. Select and copy the key manually.') }}}>{copied?<Check size={15}/>:<Copy size={15}/>} {copied?'Copied':'Copy key'}</button></div><button className="primary" onClick={()=>{setReveal(null);setCopied(false)}}>I’ve saved the key</button></section>}
    <section className="panel project-create"><div className="project-title"><FolderPlus size={20}/><h2>Create a project</h2></div><p>A project keeps your application’s events and access separate.</p><form onSubmit={create}><label>Project name<input aria-label="Project name" placeholder="e.g. Payments API" value={name} onChange={e=>setName(e.target.value)} required maxLength={100} disabled={busy || !!reveal}/></label><button className="primary" disabled={busy || !!reveal || !name.trim()}>{busy?'Working…':'Create project'}</button></form>{reveal && <p>Save and dismiss your current key before creating or rotating another.</p>}</section>
    <section className="panel"><div className="panel-title"><div><h2>Your projects</h2><p>Only projects you own appear here.</p></div><button className="text-button" disabled={loading || busy} onClick={()=>{setError('');void load()}}><RefreshCw size={14}/>Refresh</button></div>
      {loading ? <p className="empty" role="status">Loading projects…</p> : !projects.length ? <div className="empty"><FolderPlus size={28}/><h3>No projects yet</h3><p>Create your first project to generate its ingestion key.</p></div> : <div className="project-list">{projects.map(project=><article key={project.id} className="project-row"><div className="project-info"><h3>{project.name}</h3><p className="project-id">{project.id}</p><p>Created {new Date(project.created_at).toLocaleString()} · Active key: <code>{project.key_prefix ? `${project.key_prefix}…` : 'None'}</code></p></div>{rotate === project.id ? <div className="rotate-confirm"><p>Rotating immediately revokes the previous key. Any service using it will need the replacement.</p><button className="outline" disabled={busy} onClick={()=>void rotateKey(project.id)}>Confirm rotation</button><button className="text-button" disabled={busy} onClick={()=>setRotate(null)}>Cancel</button></div> : <button className="outline" disabled={busy || !!reveal} onClick={()=>setRotate(project.id)}><KeyRound size={14}/>Rotate key</button>}</article>)}</div>}
    </section>
  </div>
}
