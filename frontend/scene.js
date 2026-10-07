import * as THREE from 'three';
import {gsap} from 'gsap';
import {createLogicCore} from './logic-core.js';
import {createConstellation} from './constellation.js';
import {watchContext} from './scene-lifecycle.js';
export function mountScene(host){
 if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
 let renderer;try{renderer=new THREE.WebGLRenderer({alpha:true,antialias:true});}catch{return;}
 renderer.setPixelRatio(Math.min(devicePixelRatio,host.clientWidth<=650?1.25:1.7));host.append(renderer.domElement);renderer.domElement.setAttribute('aria-hidden','true');
 const fieldCanvas=document.createElement('canvas');fieldCanvas.className='constellation-field';fieldCanvas.setAttribute('aria-hidden','true');host.prepend(fieldCanvas);const field=createConstellation(fieldCanvas);
 const scene=new THREE.Scene(),camera=new THREE.OrthographicCamera(-14,14,12,-12,.1,140);
 scene.fog=new THREE.FogExp2(0x101416,.014);
 camera.position.set(22,18,22);camera.lookAt(0,0,0);
 const artwork=createLogicCore(THREE,scene),phase=document.querySelector('[data-scene-phase]');
 const stage={time:0};let visible=true,raf=null,disposed=false,contextLost=false;
 const media=matchMedia('(prefers-reduced-motion: reduce)');
 const timeline=gsap.timeline({repeat:-1,repeatDelay:0,paused:true});
 const labels=['Original tests pass','Challenge requests probe the repair','A remaining gap is revealed'];
 function announce(index){phase.textContent=labels[index];host.dataset.phase=String(index);document.querySelectorAll('.scene-legend li').forEach((el,i)=>el.classList.toggle('is-active',i===index));}
 timeline.call(()=>announce(0)).to(stage,{time:2.5,duration:2.5,ease:'none'}).call(()=>announce(1)).to(stage,{time:5,duration:2.5,ease:'none'}).call(()=>announce(2)).to(artwork.material.color,{r:.965,g:.639,b:.616,duration:.5}).to(artwork.material.emissive,{r:.965,g:.639,b:.616,duration:.5},'<').to(stage,{time:7,duration:2,ease:'none'}).set(artwork.material.color,{r:.612,g:.871,b:.886}).set(artwork.material.emissive,{r:.612,g:.871,b:.886});
 function draw(){raf=null;if(disposed||!visible||document.hidden)return;field.draw(timeline.totalTime());artwork.update(timeline.totalTime());const compact=host.clientWidth<=650;artwork.group.position.x=compact?0:5;artwork.group.position.z=compact?0:-5;artwork.group.rotation.y=Math.sin(timeline.totalTime()*.1)*.22;renderer.render(scene,camera);raf=requestAnimationFrame(draw);}
 function sync(){if(visible&&!document.hidden&&!disposed&&!contextLost){timeline.resume();if(raf===null)draw();}else{timeline.pause();if(raf!==null)cancelAnimationFrame(raf);raf=null;}}
 const resize=new ResizeObserver(()=>{if(disposed)return;const aspect=host.clientWidth/Math.max(1,host.clientHeight),compact=host.clientWidth<=650,d=(compact?9:10.5)/Math.min(1,aspect),ratio=Math.min(devicePixelRatio,compact?1.25:1.7);camera.left=-d*aspect;camera.right=d*aspect;camera.top=d;camera.bottom=-d;camera.updateProjectionMatrix();renderer.setPixelRatio(ratio);renderer.setSize(host.clientWidth,host.clientHeight,false);field.resize(host.clientWidth,host.clientHeight,ratio);});resize.observe(host);
 const observer=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;sync();});observer.observe(host);document.addEventListener('visibilitychange',sync);
 const stopContext=watchContext(renderer.domElement,()=>{contextLost=true;sync();host.classList.remove('scene-ready');phase.textContent='Original tests. Challenge requests. Review the repair.';},()=>{if(disposed)return;contextLost=false;host.classList.add('scene-ready');sync();});
 function dispose(){if(disposed)return;disposed=true;timeline.kill();if(raf!==null)cancelAnimationFrame(raf);observer.disconnect();resize.disconnect();document.removeEventListener('visibilitychange',sync);media.removeEventListener('change',dispose);stopContext();scene.traverse(o=>{o.geometry?.dispose();if(o.material){o.material.map?.dispose();o.material.dispose();}});renderer.dispose();renderer.domElement.remove();fieldCanvas.remove();host.classList.remove('scene-ready');phase.textContent='Original tests. Challenge requests. Review the repair.';}
 media.addEventListener('change',dispose,{once:true});host.classList.add('scene-ready');sync();
 return dispose;
}
