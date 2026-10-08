import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';

const source=(await readFile('frontend/scene-lifecycle.js','utf8')).replaceAll('export function','function');
function eventTarget(matches=false){
 const listeners=new Map();
 return {matches,listeners,addEventListener(type,fn){if(!listeners.has(type))listeners.set(type,new Set());listeners.get(type).add(fn);},removeEventListener(type,fn){listeners.get(type)?.delete(fn);},async emit(type,event={}){await Promise.all([...listeners.get(type)||[]].map(fn=>fn(event)));}};
}
function setup(small=false){
 const reduced=eventTarget(),compact=eventTarget(small);
 let enter;
 const context={matchMedia:q=>q.includes('reduced')?reduced:compact,IntersectionObserver:class{constructor(fn){enter=fn;}observe(){}disconnect(){}}};
 vm.createContext(context);vm.runInContext(source,context);
 return {watch:context.watchScene,context:context.watchContext,reduced,compact,enter:()=>enter([{isIntersecting:true}])};
}
test('narrow initial load mounts once and resizing does not dispose the scene',async()=>{
 const c=setup(true);let mounts=0,stops=0;
 c.watch({},async()=>({mountScene(){mounts++;return()=>stops++;}}));
 await c.enter();assert.equal(mounts,1);
 c.compact.matches=false;await c.compact.emit('change');assert.equal(mounts,1);
 c.compact.matches=true;await c.compact.emit('change');assert.equal(stops,0);
 c.compact.matches=false;await c.compact.emit('change');assert.equal(mounts,1);
});
test('reduced motion toggles preserve fallback and recover without duplicate scenes',async()=>{
 const c=setup();let mounts=0,stops=0;
 const dispose=c.watch({},async()=>({mountScene(){mounts++;return()=>stops++;}}));
 await c.enter();await c.enter();assert.equal(mounts,1);
 c.reduced.matches=true;await c.reduced.emit('change');assert.equal(stops,1);
 c.reduced.matches=false;await c.reduced.emit('change');assert.equal(mounts,2);
 dispose();await c.enter();assert.equal(mounts,2);assert.equal(stops,2);
});
test('late module completion cannot mount after reduced motion is enabled',async()=>{
 const c=setup();let resolve,mounts=0;
 c.watch({},()=>new Promise(done=>resolve=done));
 const started=c.enter();c.reduced.matches=true;await c.reduced.emit('change');
 resolve({mountScene(){mounts++;return()=>{};}});await started;
 assert.equal(mounts,0);
});
test('lost WebGL context permits browser restoration and removes recovery listeners on cleanup',async()=>{
 const c=setup(),canvas=eventTarget();let prevented=0,lost=0,restored=0;
 const stop=c.context(canvas,()=>lost++,()=>restored++);
 await canvas.emit('webglcontextlost',{preventDefault(){prevented++;}});
 await canvas.emit('webglcontextrestored');
 assert.deepEqual([prevented,lost,restored],[1,1,1]);
 stop();await canvas.emit('webglcontextrestored');assert.equal(restored,1);
});
