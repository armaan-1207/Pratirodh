import { gsap } from 'gsap';

// Progressive enhancement: every panel and native form is usable without JavaScript.
for (const group of document.querySelectorAll('[data-tabs]')) {
 const tabs=[...group.querySelectorAll('[data-tab]')];
 const panels=tabs.map(t=>document.querySelector(t.getAttribute('href')));
 group.setAttribute('role','tablist');
 function activate(index,focus=false) {
  tabs.forEach((t,i)=>{t.setAttribute('aria-selected',String(i===index));t.tabIndex=i===index?0:-1;panels[i].hidden=i!==index;});
  if(focus) tabs[index].focus();
 }
 tabs.forEach((t,i)=>{
  t.id ||= `tab-${panels[i].id}`;t.setAttribute('role','tab');t.setAttribute('aria-controls',panels[i].id);
  panels[i].setAttribute('role','tabpanel');panels[i].setAttribute('aria-labelledby',t.id);panels[i].tabIndex=0;
  t.addEventListener('click',e=>{e.preventDefault();activate(i);history.replaceState(null,'',t.getAttribute('href'));});
  t.addEventListener('keydown',e=>{let n=i;if(e.key==='ArrowRight')n=(i+1)%tabs.length;else if(e.key==='ArrowLeft')n=(i-1+tabs.length)%tabs.length;else if(e.key==='Home')n=0;else if(e.key==='End')n=tabs.length-1;else return;e.preventDefault();activate(n,true);});
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
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const heroItems=document.querySelectorAll('.hero-copy > *');
if(!reduced.matches&&heroItems.length){gsap.from(heroItems,{y:16,opacity:0,duration:.65,stagger:.09,clearProps:'all'});}
const scene=document.querySelector('#verification-scene');
if(scene&&!reduced.matches&&matchMedia('(min-width: 651px)').matches){const observer=new IntersectionObserver(async entries=>{if(entries.some(e=>e.isIntersecting)){observer.disconnect();try{const {mountScene}=await import('./scene.js');mountScene(scene);}catch{/* The static diagram remains available. */}}},{rootMargin:'100px'});observer.observe(scene);}
