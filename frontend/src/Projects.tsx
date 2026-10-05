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
  const [deleting, setDeleting] = useState<Project | null>(null)
  const [confirmation, setConfirmation] = useState('')
  const [deleteError, setDeleteError] = useState('')
  const [notice, setNotice] = useState('')
  async function request(path = '', body?: unknown, method?: string) {
    const response = await fetch(`${api}/api/v1/projects${path}`, {
      method: method || (body === undefined ? 'GET' : 'POST'), credentials: 'include', cache: 'no-store',
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
  async function deleteProject(event: FormEvent) {
    event.preventDefault()
    if (!deleting || confirmation !== deleting.name || busy) return
    setBusy(true); setDeleteError(''); setError(''); setNotice('')
    try {
      await request(`/${deleting.id}`, { confirmation_name: confirmation }, 'DELETE')
      setProjects(current => current.filter(project => project.id !== deleting.id))
      setNotice(`Project “${deleting.name}” and its related data were deleted.`)
      setDeleting(null); setConfirmation(''); setRotate(null)
      await load()
    } catch (e) {
      setDeleteError(e instanceof Error ? `Deletion could not be confirmed: ${e.message} Refresh the list before retrying.` : 'Deletion could not be confirmed. Refresh the list before retrying.')
    } finally { setBusy(false) }
  }
  return <div className="projects-page">
    {notice && <div className="setup-note" role="status">{notice}</div>}
    {deleting && <section className="panel delete-project" aria-label="Delete project confirmation">
      <h2>Delete {deleting.name}?</h2><p>This permanently deletes this project, all its keys, and existing related data. This cannot be undone.</p>
      <form onSubmit={deleteProject}><label htmlFor="delete-project-name">Type <strong>{deleting.name}</strong> exactly to confirm</label>
        <input id="delete-project-name" autoFocus autoComplete="off" value={confirmation} onChange={e=>setConfirmation(e.target.value)} disabled={busy} maxLength={100}/>
        {deleteError && <p className="auth-error" role="alert">{deleteError}</p>}
        <div className="delete-actions"><button className="danger-button" disabled={busy || confirmation !== deleting.name}>{busy ? 'Deleting…' : 'Permanently delete project'}</button><button type="button" className="outline" disabled={busy} onClick={()=>{setDeleting(null);setConfirmation('');setDeleteError('')}}>Cancel deletion</button></div>
      </form></section>}
    <div className="setup-note">Projects, keys, and event ingestion are live. The overview and log explorer still show sample data.</div>
    {error && <div className="auth-error" role="alert">{error} <button onClick={()=>{setError('');void load()}} disabled={busy}>Retry loading</button></div>}
    {reveal && <section className="key-reveal" aria-label="New ingestion key"><div className="project-title"><KeyRound size={21}/><h2>Save your key for {reveal.name}</h2></div><p>This is the only time this key is shown. Save it somewhere secure before leaving this page. If lost, rotate it to create a replacement.</p><div className="key-value"><code data-testid="ingestion-key">{reveal.value}</code><button className="outline" onClick={async()=>{try { await navigator.clipboard.writeText(reveal.value);setCopied(true) } catch { setError('Clipboard unavailable. Select and copy the key manually.') }}}>{copied?<Check size={15}/>:<Copy size={15}/>} {copied?'Copied':'Copy key'}</button></div><button className="primary" onClick={()=>{setReveal(null);setCopied(false)}}>I’ve saved the key</button></section>}
    <section className="panel project-create"><div className="project-title"><FolderPlus size={20}/><h2>Create a project</h2></div><p>A project keeps your application’s events and access separate.</p><form onSubmit={create}><label>Project name<input aria-label="Project name" placeholder="e.g. Payments API" value={name} onChange={e=>setName(e.target.value)} required maxLength={100} disabled={busy || !!reveal || !!deleting}/></label><button className="primary" disabled={busy || !!reveal || !!deleting || !name.trim()}>{busy?'Working…':'Create project'}</button></form>{reveal && <p>Save and dismiss your current key before creating or rotating another.</p>}</section>
    <section className="panel"><div className="panel-title"><div><h2>Your projects</h2><p>Only projects you own appear here.</p></div><button className="text-button" disabled={loading || busy} onClick={()=>{setError('');void load()}}><RefreshCw size={14}/>Refresh</button></div>
      {loading ? <p className="empty" role="status">Loading projects…</p> : !projects.length ? <div className="empty"><FolderPlus size={28}/><h3>No projects yet</h3><p>Create your first project to generate its ingestion key.</p></div> : <div className="project-list">{projects.map(project=><article key={project.id} className="project-row"><div className="project-info"><h3>{project.name}</h3><p className="project-id">{project.id}</p><p>Created {new Date(project.created_at).toLocaleString()} · Active key: <code>{project.key_prefix ? `${project.key_prefix}…` : 'None'}</code></p></div>{rotate === project.id ? <div className="rotate-confirm"><p>Rotating immediately revokes the previous key. Any service using it will need the replacement.</p><button className="outline" disabled={busy} onClick={()=>void rotateKey(project.id)}>Confirm rotation</button><button className="text-button" disabled={busy} onClick={()=>setRotate(null)}>Cancel</button></div> : <button className="outline" disabled={busy || !!reveal || !!deleting} onClick={()=>setRotate(project.id)}><KeyRound size={14}/>Rotate key</button>}<button className="danger-button" disabled={busy || !!reveal || !!deleting} onClick={()=>{setDeleting(project);setConfirmation('');setDeleteError('');setNotice('');setRotate(null)}}>Delete project</button></article>)}</div>}
    </section>
  </div>
}
