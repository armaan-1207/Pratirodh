import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
gsap.registerPlugin(ScrollTrigger);
const reduced=matchMedia('(prefers-reduced-motion: reduce)');

// 21st.dev / Motion Primitives spotlight pattern, native DOM implementation.
// Pointer feedback follows the evidence surface; keyboard focus gets the same edge.
const evidence=document.querySelector('.evidence-stack');
if(evidence){
 evidence.addEventListener('pointermove',event=>{
  if(reduced.matches||event.pointerType==='touch')return;
  const card=event.target.closest('.evidence-step');if(!card)return;
  const rect=card.getBoundingClientRect();
  card.style.setProperty('--spot-x',`${event.clientX-rect.left}px`);
  card.style.setProperty('--spot-y',`${event.clientY-rect.top}px`);
 });
}

// Progressive enhancement: every panel and native form is usable without JavaScript.
for (const group of document.querySelectorAll('[data-tabs]')) {
 const tabs=[...group.querySelectorAll('[data-tab]')];
 const panels=tabs.map(t=>document.querySelector(t.getAttribute('href')));
 group.setAttribute('role','tablist');
 // Sliding selection surface adapted from Julien Thibeaut's Animated Tabs
 // on 21st.dev / Motion Primitives; use GSAP with the existing Jinja markup.
 let selected=0,highlight;
 if(group.classList.contains('example-selector')){
  highlight=document.createElement('span');highlight.className='tab-highlight';highlight.setAttribute('aria-hidden','true');group.prepend(highlight);
  new ResizeObserver(()=>moveHighlight(false)).observe(group);
 }
 function moveHighlight(animate){if(!highlight)return;const t=tabs[selected],rect=t.getBoundingClientRect(),base=group.getBoundingClientRect();highlight.style.width=`${rect.width}px`;highlight.style.height=`${rect.height}px`;const target={x:rect.left-base.left,y:rect.top-base.top,transformOrigin:'0 0'};gsap.killTweensOf(highlight);if(animate&&!reduced.matches)gsap.to(highlight,{...target,duration:.4,ease:'power3.out'});else gsap.set(highlight,target);}

 function activate(index,focus=false,animate=false) {
  selected=index;
  tabs.forEach((t,i)=>{t.setAttribute('aria-selected',String(i===index));t.tabIndex=i===index?0:-1;panels[i].hidden=i!==index;});
  moveHighlight(animate);
  if(focus) tabs[index].focus();
  if(animate&&!reduced.matches){gsap.killTweensOf(panels);gsap.fromTo(panels[index],{y:8,opacity:.55},{y:0,opacity:1,duration:.28,ease:'power2.out',clearProps:'transform,opacity'});}
 }
 tabs.forEach((t,i)=>{
  t.id ||= `tab-${panels[i].id}`;t.setAttribute('role','tab');t.setAttribute('aria-controls',panels[i].id);
  panels[i].setAttribute('role','tabpanel');panels[i].setAttribute('aria-labelledby',t.id);panels[i].tabIndex=0;
  t.addEventListener('click',e=>{e.preventDefault();activate(i,false,true);history.replaceState(null,'',t.getAttribute('href'));});
  t.addEventListener('keydown',e=>{let n=i;if(e.key==='ArrowRight')n=(i+1)%tabs.length;else if(e.key==='ArrowLeft')n=(i-1+tabs.length)%tabs.length;else if(e.key==='Home')n=0;else if(e.key==='End')n=tabs.length-1;else return;e.preventDefault();activate(n,true,true);});
 });
 activate(Math.max(0,tabs.findIndex(t=>t.getAttribute('href')===(location.hash||group.dataset.defaultTab))));
}
const filters=document.querySelector('.filters');
if(filters){
 filters.hidden=false;
 const rows=[...document.querySelectorAll('.run-row[data-decision]')];
 const search=document.querySelector('#history-search');
 const keys=['decision','cwe','origin'];
 const stale=document.querySelector('#include-stale');
 function filter(){let count=0;for(const row of rows){const show=(stale.checked||row.dataset.current==='true')&&row.textContent.toLowerCase().includes(search.value.toLowerCase())&&keys.every(k=>!document.querySelector(`#filter-${k}`).value||(k==='origin'?row.dataset[k].split(',').includes(document.querySelector(`#filter-${k}`).value):row.dataset[k]===document.querySelector(`#filter-${k}`).value));row.hidden=!show;if(show)count++;}document.querySelector('#history-count').textContent=`${count} of ${rows.length} loaded recent records shown`;document.querySelector('#no-matches').hidden=count>0;}
 filters.addEventListener('input',filter);
 stale.addEventListener('change',()=>{filter();const url=new URL(location.href);if(stale.checked)url.searchParams.set('history','all');else url.searchParams.delete('history');history.replaceState(null,'',url);});
 filter();
 document.querySelector('#clear-filters').addEventListener('click',()=>{filters.querySelectorAll('input,select').forEach(x=>x.value='');stale.checked=false;stale.dispatchEvent(new Event('change'));search.focus();});
}
const failed=document.querySelector('#failed-only');
if(failed){failed.parentElement.hidden=false;failed.addEventListener('change',()=>document.querySelectorAll('.check').forEach(c=>c.hidden=failed.checked&&c.dataset.status==='PASS'));}
for(const form of document.querySelectorAll('[data-launch]')){
 form.addEventListener('submit',async e=>{e.preventDefault();const button=form.querySelector('button');const status=form.querySelector('[role=status]');button.disabled=true;status.textContent='Submitting to the local execution service…';
 try{const response=await fetch(form.action,{method:'POST',body:new FormData(form),credentials:'same-origin'});if(response.ok&&response.redirected&&new URL(response.url).pathname.startsWith('/jobs/')){location.assign(response.url);return;}status.textContent=response.status===409?'Another job is active. Wait for its execution to finish.':response.status===403?'Execution is unavailable: read-only mode or an expired session. Reload the workspace.':'Execution could not start. Check the local service and scenario.';}catch{status.textContent='Connection unavailable. Reload the workspace to check whether the job started before retrying.';}button.disabled=false;});
}
const runtime=document.querySelector('[data-runtime]');
if(runtime){const refresh=runtime.querySelector('[data-runtime-refresh]');async function check(){refresh.disabled=true;try{const response=await fetch('/api/runtime',{credentials:'same-origin',cache:'no-store'});if(!response.ok)throw Error();const data=await response.json();runtime.querySelector('[data-runtime-docker]').textContent=data.docker;runtime.querySelector('[data-runtime-model]').textContent=data.model;runtime.querySelector('[data-runtime-message]').textContent='Curated demonstration needs Docker only. Combined repair can try a template if the model is unavailable.';}catch{runtime.querySelector('[data-runtime-message]').textContent='Setup status unavailable. Refresh the page or check local setup.';}finally{refresh.disabled=false;}}refresh.addEventListener('click',check);check();}
const stageNames={detect:'Detecting a finding',reproduce:'Reproducing the original violation',generate:'Proposing a repair',verify:'Verifying the candidate',challenge:'Challenging the repair', 'security-checks':'Executing security requests',sign:'Signing the evidence',complete:'Review the results'};
const job=document.querySelector('[data-job]');
if(job){
 const state=document.querySelector('#job-status'),step=document.querySelector('#job-step'),message=document.querySelector('#poll-status'),retry=document.querySelector('#retry-poll'),runs=document.querySelector('#job-runs');let active=job.dataset.status==='RUNNING',timer;let previousRuns=[...runs.querySelectorAll('a')].map(a=>a.getAttribute('href').split('/').pop()).join(',');
 async function poll(){if(document.hidden)return;try{const r=await fetch(`/api/jobs/${encodeURIComponent(job.dataset.job)}`,{credentials:'same-origin',cache:'no-store'});if(!r.ok)throw Error();const data=await r.json();state.textContent=data.status;step.textContent=data.status==='RUNNING'?(stageNames[data.stage]||data.step):data.step;document.querySelector('#job-elapsed').textContent=`${data.elapsed_seconds}s`;document.querySelector('#job-attempt').textContent=`Candidate ${data.candidate||'not started'}${data.generator?' · '+data.generator:''}`;document.querySelector('#job-demo-step').textContent=data.demo_step?`Demonstration ${data.demo_step} of 3`:'';job.querySelectorAll('[data-stage]').forEach(el=>{if(el.dataset.stage===data.stage)el.setAttribute('aria-current','step');else el.removeAttribute('aria-current');});if(data.runs.join(',')!==previousRuns){previousRuns=data.runs.join(',');runs.replaceChildren();data.runs.forEach((id,i)=>{const a=document.createElement('a');a.className='run-row';a.href=`/runs/${encodeURIComponent(id)}`;const names=['Basic check of weak repair','Full check of weak repair','Full check of corrected repair'];a.textContent=`${job.dataset.demo==='true'?names[i]:`Open signed result ${i+1}`} · ${id.slice(0,12)} ↗`;runs.append(a);});}active=data.status==='RUNNING';message.textContent=active?'Connected. Waiting for the next backend stage.':data.status==='ERROR'?'Execution failed. Open any available evidence, then check local setup and CLI logs.':'Execution complete. Open a signed result below.';retry.hidden=true;if(active)timer=setTimeout(poll,2500);}catch{message.textContent='Status connection unavailable. Execution may still be running; no result has been assumed.';retry.hidden=false;}}
 retry.addEventListener('click',poll);document.addEventListener('visibilitychange',()=>{clearTimeout(timer);if(!document.hidden&&active)poll();});if(active)poll();
}
const heroItems=document.querySelectorAll('.hero-copy > *');
const workflow=document.querySelector('[data-workflow]');
if(workflow){const steps=[...workflow.children];const open=index=>{workflow.style.setProperty('--workflow-columns',steps.map((_,i)=>i===index?'1.8fr':'1fr').join(' '));steps.forEach((step,i)=>{step.toggleAttribute('data-open',i===index);step.querySelector('button').setAttribute('aria-expanded',String(i===index));step.querySelector('.workflow-detail').hidden=i!==index;});};steps.forEach((step,i)=>step.querySelector('button').addEventListener('click',()=>open(i)));open(0);}
if(heroItems.length){
 const hero=document.querySelector('.hero');let heroVisible=false;
 const syncBackdrop=()=>hero.classList.toggle('motion-active',heroVisible&&!document.hidden&&!reduced.matches);
 new IntersectionObserver(entries=>{heroVisible=entries[0].isIntersecting;syncBackdrop();}).observe(hero);
 document.addEventListener('visibilitychange',syncBackdrop);reduced.addEventListener('change',syncBackdrop);
 const motion=gsap.matchMedia();
 motion.add('(prefers-reduced-motion: no-preference)',()=>{
  gsap.from([...heroItems].filter(el=>el.tagName!=='H1'),{y:22,opacity:0,duration:.8,stagger:.12,ease:'power3.out',clearProps:'transform,opacity'});
  // Masked line reveal informed by ThreeUI Diagnostics Panel typography.
  gsap.from('.hero-line-text',{yPercent:105,duration:1.05,stagger:.14,ease:'power4.out',clearProps:'transform'});
  const reveals=new IntersectionObserver(entries=>{for(const entry of entries){if(entry.isIntersecting){reveals.unobserve(entry.target);gsap.from(entry.target,{y:26,opacity:0,duration:.75,ease:'power3.out',clearProps:'transform,opacity'});}}},{threshold:.08});
  document.querySelectorAll('[data-reveal]').forEach(el=>reveals.observe(el));
  const copy=document.querySelector('[data-scrub-copy]');
  if(copy){const lines=copy.innerText.split('\n');copy.replaceChildren();lines.forEach((line,i)=>{if(i)copy.append(document.createElement('br'));for(const word of line.split(' ')){const span=document.createElement('span');span.textContent=word+' ';copy.append(span);}});gsap.fromTo(copy.querySelectorAll('span'),{opacity:.2},{opacity:1,stagger:.1,ease:'none',scrollTrigger:{trigger:copy,start:'top 85%',end:'top 45%',scrub:1}});}
  const cards=[...document.querySelectorAll('.evidence-step')];cards.slice(0,-1).forEach((card,i)=>gsap.to(card,{scale:.95,y:-8,ease:'none',scrollTrigger:{trigger:cards[i+1],start:'top 70%',end:'top 24%',scrub:1}}));
  return ()=>reveals.disconnect();
 });
}
reduced.addEventListener('change',()=>{if(reduced.matches){const panels=document.querySelectorAll('[role=tabpanel]');gsap.killTweensOf(panels);gsap.set(panels,{clearProps:'transform,opacity'});}});
const scene=document.querySelector('#verification-scene');
if(scene&&!reduced.matches&&matchMedia('(min-width: 651px)').matches){const observer=new IntersectionObserver(async entries=>{if(entries.some(e=>e.isIntersecting)){observer.disconnect();try{const {mountScene}=await import('./scene.js');mountScene(scene);}catch{/* The static diagram remains available. */}}},{rootMargin:'100px'});observer.observe(scene);}
