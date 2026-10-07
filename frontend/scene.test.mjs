import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
// Exercise actual scene entry code in a renderer-free environment.
const source=(await readFile('frontend/scene.js','utf8')).replace(/^import .*;$/mg,'').replace('export function','function');
function sceneContext(match,throwRenderer=false){let renders=0;const context={matchMedia:q=>({matches:match(q)}),THREE:{WebGLRenderer:class{constructor(){renders++;if(throwRenderer)throw Error('WebGL unavailable');}}}};vm.createContext(context);vm.runInContext(source,context);return {mount:context.mountScene,renders:()=>renders};}
test('reduced motion keeps static diagram without constructing WebGL',()=>{const c=sceneContext(q=>q.includes('reduced-motion'));c.mount({});assert.equal(c.renders(),0);});
test('small screens attempt WebGL and retain fallback when graphics are unavailable',()=>{const c=sceneContext(q=>q.includes('max-width'),true);assert.doesNotThrow(()=>c.mount({}));assert.equal(c.renders(),1);});
test('unavailable WebGL returns to existing static diagram',()=>{const c=sceneContext(()=>false,true);assert.doesNotThrow(()=>c.mount({}));assert.equal(c.renders(),1);});
