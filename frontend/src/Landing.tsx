import { useState } from 'react'
import { Activity, ArrowDown, ArrowRight, Check, CheckCheck, ChevronRight, Code2, KeyRound, Layers, Radio, Search, ShieldCheck, Sparkles, Terminal, X } from 'lucide-react'
import './landing.css'

const samples = [
  { id: 'demo-01', time: '14:32:51', level: 'ERROR', service: 'payment-api', message: 'Database connection timed out', status: 500, latency: 104, exception: 'DatabaseTimeout' },
  { id: 'demo-02', time: '14:32:48', level: 'INFO', service: 'gateway', message: 'Request completed', status: 200, latency: 24, exception: null },
  { id: 'demo-03', time: '14:32:45', level: 'INFO', service: 'inventory-api', message: 'Request completed', status: 200, latency: 38, exception: null },
]

export default function Landing() {
  const [selected, setSelected] = useState<string | null>(null)
  const [errorsOnly, setErrorsOnly] = useState(false)
  const [query, setQuery] = useState('')
  function closeSample(id: string) { setSelected(null); document.getElementById(`sample-trigger-${id}`)?.focus() }
  const filtered = samples.filter(item => (!errorsOnly || item.level === 'ERROR') && `${item.message} ${item.service}`.toLowerCase().includes(query.toLowerCase()))
  return <div className="landing">
    <a className="lp-skip" href="#landing-main">Skip to content</a>
    <header className="lp-nav"><a className="lp-logo" href="/" aria-label="Tracely home"><Activity/>tracely<span>.</span></a>
      <nav aria-label="Main navigation"><a className="lp-section-link" href="#how-it-works">How it works</a><a className="lp-section-link" href="#features">Features</a><a href="/?auth=login">Sign in</a><a className="lp-button lp-small" href="/?auth=register">Sign up <ArrowRight size={15}/></a></nav>
    </header>
    <main id="landing-main" tabIndex={-1}>
      <section className="lp-hero lp-wrap" aria-labelledby="hero-title"><div className="lp-hero-copy"><span className="lp-eyebrow"><span className="lp-status-dot"/> A LITTLE LESS NOISE. A LOT MORE CLARITY.</span><h1 id="hero-title">Stop guessing.<br/>Start <span>tracing<svg viewBox="0 0 300 20" aria-hidden="true"><path d="M3 14 Q120 0 292 11 M24 19 Q160 7 270 17"/></svg></span>.</h1><p>Bring your application events together, spot repeated failures, and see the evidence behind them.</p><div className="lp-actions"><a className="lp-button" href="/?auth=register">Create an account <ArrowRight size={18}/></a><a className="lp-text-link" href="#product-preview">Take a little look <ArrowDown size={16}/></a></div><div className="lp-hero-note"><Code2 size={16}/> Built for your local development workflow.</div></div>
        <figure className="lp-signal"><figcaption><span className="lp-tiny-dot"/> Illustrated workflow</figcaption><div className="lp-signal-canvas" role="img" aria-label="Application events flow into a detected incident">
          <svg className="lp-tracks" viewBox="0 0 500 360" aria-hidden="true"><path d="M15 85 H150 Q200 85 200 160 V200 Q200 250 260 250 H480"/><path d="M30 180 H135 Q175 180 175 230 Q175 300 250 300 H460"/><path d="M95 345 V300 Q95 240 155 240 H250 Q300 240 300 170 V25"/><circle className="lp-traveler" r="6" cx="200" cy="180"/></svg>
          <div className="lp-float lp-request"><span className="lp-card-label"><Terminal size={14}/> payment-api</span><strong><span className="lp-error-dot"/> Request failed</strong><code>500 · DatabaseTimeout</code></div>
          <div className="lp-float lp-success"><CheckCheck size={20}/><div><strong>Request completed</strong><code>200 · gateway</code></div></div>
          <div className="lp-float lp-incident"><span className="lp-incident-icon"><Radio size={25}/></span><span className="lp-card-label">A PATTERN EMERGES</span><strong>Incident detected.</strong><span>Repeated failures, brought together.</span><div className="lp-mini-events"><i/><i/><i/><i/><i/><i/><i/><i/></div></div>
          <span className="lp-scribble" aria-hidden="true">oh, there it is! <Sparkles size={21}/></span>
        </div></figure>
      </section>
      <div className="lp-ribbon" aria-label="Product principles"><span><Layers size={17}/> Events with context</span><span><ShieldCheck size={17}/> Project-scoped access</span><span><Radio size={17}/> Rules before guesswork</span></div>
      <section className="lp-wrap lp-preview-section" id="product-preview" aria-labelledby="preview-title"><div className="lp-section-heading"><div><span className="lp-eyebrow">MEET YOUR EVENT EXPLORER</span><h2 id="preview-title">The details.<br/>Without the digging.</h2></div><p>Choose a project, filter the noise, and open an event. Your next clue could be one click away.</p></div>
        <div className="lp-browser"><div className="lp-browser-bar"><span aria-hidden="true"><i/><i/><i/></span><span>tracely / events</span><span className="lp-demo-label">Interactive demo · sample events</span></div><div className="lp-preview-body"><div className="lp-preview-title"><div><span className="lp-eyebrow">DEMO PROJECT</span><h3>Stored events</h3></div><span className="lp-demo-project">Demo application <ChevronRight size={14}/></span></div><div className="lp-preview-filters"><label><Search size={17}/><input aria-label="Search sample events" value={query} onChange={e => { setQuery(e.target.value); setSelected(null) }} placeholder="Try ‘payment’…"/></label><button aria-pressed={errorsOnly} onClick={() => { setErrorsOnly(value => !value); setSelected(null) }}>{errorsOnly ? 'Errors only' : 'All levels'}<span className="lp-filter-dot"/></button></div>
          <div className="lp-demo-columns" aria-hidden="true"><span>TIME / LEVEL</span><span>SERVICE / MESSAGE</span><span>DETAILS</span></div>
          {filtered.map(item => <div className="lp-demo-event" key={item.id} onKeyDown={e => { if (e.key === 'Escape' && selected === item.id) { e.stopPropagation(); closeSample(item.id) } }}><button id={`sample-trigger-${item.id}`} className="lp-demo-row" aria-expanded={selected === item.id} aria-controls={`sample-${item.id}`} onClick={() => setSelected(selected === item.id ? null : item.id)}><span><time>{item.time} UTC</time><span className={`lp-level ${item.level === 'ERROR' ? 'lp-level-error' : ''}`}>{item.level}</span></span><span><strong>{item.service}</strong><span>{item.message}</span></span><ArrowRight size={17}/><span className="sr-only">Inspect sample event {item.id}</span></button>{selected === item.id && <div className="lp-demo-detail" id={`sample-${item.id}`}><div><strong>Sample event details</strong><button aria-label="Close sample details" onClick={() => closeSample(item.id)}><X size={16}/></button></div><dl><div><dt>Status</dt><dd>{item.status}</dd></div><div><dt>Latency</dt><dd>{item.latency} ms</dd></div><div><dt>Exception</dt><dd>{item.exception || 'None'}</dd></div></dl><p>Synthetic example. These are not your application’s events.</p></div>}</div>)}
          {!filtered.length && <p className="lp-demo-empty" role="status">No sample events match. <button onClick={() => { setQuery(''); setErrorsOnly(false) }}>Clear filters</button></p>}
          <p className="lp-preview-foot">A small, interactive example of the live event explorer. No account needed to try it.</p></div></div>
      </section>
      <section className="lp-how" id="how-it-works" aria-labelledby="how-title"><div className="lp-wrap"><span className="lp-eyebrow">THREE STEPS. ONE CLEARER PICTURE.</span><h2 id="how-title">From “what happened?”<br/>to “let’s take a look.”</h2><div className="lp-steps">{[
        { icon: KeyRound, title: 'Connect your app', copy: 'Create a project and get an ingestion key. A dedicated home for your application’s signals.' },
        { icon: Activity, title: 'Send the signals', copy: 'Collect requests, errors, and useful context. Explore the details as events arrive.' },
        { icon: Radio, title: 'Spot repeated failures', copy: 'The background detector tracks sustained request failures and confirms recovery.' },
      ].map((step, index) => <article key={step.title}><div className={`lp-step-art lp-step-${index}`} aria-hidden="true"><step.icon size={43}/><span>0{index + 1}</span></div><h3>{step.title}</h3><p>{step.copy}</p></article>)}</div></div></section>
      <section className="lp-wrap lp-features" id="features" aria-labelledby="features-title"><div className="lp-section-heading"><div><span className="lp-eyebrow">REAL FEATURES. RIGHT NOW.</span><h2 id="features-title">A good place<br/>to start looking.</h2></div><p>The essentials for collecting evidence and catching patterns in your local environment.</p></div><div className="lp-feature-grid">{[
        { icon: ShieldCheck, title: 'Your own workspace', copy: 'Email or Google sign-in, plus password recovery with configured email delivery.' },
        { icon: KeyRound, title: 'Projects & keys', copy: 'Keep application data separate and manage ingestion access with keys you can rotate.' },
        { icon: Search, title: 'Live event explorer', copy: 'Search, filter, and inspect stored events, from status codes to stack traces.' },
        { icon: Radio, title: 'Background detection', copy: 'Detect sustained request failures, browse incidents, and inspect grouped exception evidence.' },
      ].map(item => <article key={item.title}><item.icon size={25}/><h3>{item.title}</h3><p>{item.copy}</p><span><Check size={14}/> Available today</span></article>)}</div><p className="lp-availability"><Radio size={17}/> Project overviews, incident details, and exception grouping use stored evidence.</p></section>
      <section className="lp-wrap"><div className="lp-upcoming"><div><span className="lp-eyebrow">UPCOMING — NOT AVAILABLE YET</span><h2>Next on the<br/>workbench.</h2><p>More ways to connect the evidence.<br/>One thoughtful step at a time.</p></div><ul><li><Search/>Evidence-based investigations</li><li><Sparkles/>Optional local AI assistance</li></ul></div></section>
      <section className="lp-wrap lp-final"><div className="lp-final-doodle" aria-hidden="true"><Activity size={40}/></div><span className="lp-eyebrow">YOUR FIRST SIGNAL IS A GOOD START.</span><h2>Something broke.<br/><span>Follow the signal.</span></h2><p>Start with one project and follow your first signal.</p><a className="lp-button" href="/?auth=register">Create an account <ArrowRight size={18}/></a><a className="lp-final-login" href="/?auth=login">Already here? Sign in</a></section>
    </main>
    <footer className="lp-footer lp-wrap"><a className="lp-logo" href="/" aria-label="Tracely home"><Activity/>tracely<span>.</span></a><span>Make sense of the signals.</span><a href="#landing-main">Back to top ↑</a></footer>
  </div>
}
