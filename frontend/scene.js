import * as THREE from 'three';
import {gsap} from 'gsap';
export function mountScene(host){
 if(matchMedia("(prefers-reduced-motion: reduce)").matches||matchMedia("(max-width: 650px)").matches)return;
 let renderer;try{renderer=new THREE.WebGLRenderer({alpha:true,antialias:true});}catch{return;}
 renderer.setPixelRatio(Math.min(devicePixelRatio,1.7));host.append(renderer.domElement);renderer.domElement.setAttribute('aria-hidden','true');
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(36,1,.1,100),assembly=new THREE.Group();scene.add(assembly);camera.position.set(6,5.5,8);camera.lookAt(0,0,0);
 const cyan=0x9cdee2,red=0xf6a39d;
 function label(text,y,color){const canvas=document.createElement('canvas');canvas.width=640;canvas.height=70;const ctx=canvas.getContext('2d');ctx.font='26px monospace';ctx.fillStyle=color;ctx.fillText(text,12,44);const texture=new THREE.CanvasTexture(canvas);const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,transparent:true}));sprite.scale.set(3.9,.43,1);sprite.position.set(0,y,1.75);assembly.add(sprite);}
 for(let i=0;i<3;i++){const y=1.45-i*1.45;const geometry=new THREE.BoxGeometry(3.8,.055,2.7);const plate=new THREE.Mesh(geometry,new THREE.MeshBasicMaterial({color:i===2?0x542e31:0x477078,transparent:true,opacity:.26,depthWrite:false}));plate.position.y=y;assembly.add(plate);const edge=new THREE.LineSegments(new THREE.EdgesGeometry(geometry),new THREE.LineBasicMaterial({color:i===2?red:cyan,transparent:true,opacity:.75}));edge.position.y=y;assembly.add(edge);label(['01  ORIGINAL TESTS','02  CHALLENGE REQUEST','03  PRIVATE FILE EXPOSED'][i],y+.25,i===2?'#f6a39d':'#b8dce0');}
 const path=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-.8,2.4,0),new THREE.Vector3(-.8,1.45,0),new THREE.Vector3(.35,0,0),new THREE.Vector3(.35,-1.45,0)]),new THREE.LineDashedMaterial({color:cyan,dashSize:.13,gapSize:.1}));path.computeLineDistances();assembly.add(path);
 const cube=new THREE.Mesh(new THREE.IcosahedronGeometry(.22,0),new THREE.MeshBasicMaterial({color:cyan,wireframe:true}));cube.position.set(-.8,2.1,0);assembly.add(cube);
 const failure=new THREE.Mesh(new THREE.OctahedronGeometry(.2),new THREE.MeshBasicMaterial({color:red}));failure.position.set(.35,-1.45,0);assembly.add(failure);
 const timeline=gsap.timeline({repeat:-1,repeatDelay:1.6,paused:true});timeline.to(cube.position,{y:1.45,duration:1}).to(cube.position,{x:.35,y:0,duration:1.4}).to(cube.position,{y:-1.45,duration:1}).to(cube.material.color,{r:.96,g:.64,b:.62,duration:.3}).to(cube,{visible:false,duration:.01}).set(cube.position,{x:-.8,y:2.1}).set(cube.material.color,{r:.61,g:.87,b:.89}).set(cube,{visible:true});
 let visible=true,raf=null,disposed=false,userPaused=false;const media=matchMedia('(prefers-reduced-motion: reduce)'),small=matchMedia('(max-width: 650px)');
 function draw(){raf=null;if(disposed||!visible||document.hidden)return;renderer.render(scene,camera);raf=requestAnimationFrame(draw);}
 function sync(){if(visible&&!document.hidden&&!disposed){if(!userPaused)timeline.resume();if(raf===null)draw();}else{timeline.pause();if(raf!==null)cancelAnimationFrame(raf);raf=null;}}
 const resize=new ResizeObserver(()=>{if(disposed)return;renderer.setSize(host.clientWidth,host.clientHeight,false);camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix();});resize.observe(host);
 const observer=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;sync();});observer.observe(host);document.addEventListener('visibilitychange',sync);
 const pause=document.querySelector('#pause-scene');pause.hidden=false;pause.addEventListener('click',()=>{userPaused=!userPaused;pause.textContent=userPaused?'Resume illustration':'Pause illustration';if(userPaused)timeline.pause();else sync();});
 const button=document.querySelector('#rotate-scene');button.hidden=false;button.addEventListener('click',()=>gsap.to(assembly.rotation,{y:assembly.rotation.y+.45,duration:.6}));
 function dispose(){if(disposed)return;disposed=true;timeline.kill();gsap.killTweensOf(assembly.rotation);if(raf!==null)cancelAnimationFrame(raf);observer.disconnect();resize.disconnect();document.removeEventListener('visibilitychange',sync);scene.traverse(o=>{o.geometry?.dispose();if(o.material){o.material.map?.dispose();o.material.dispose();}});renderer.dispose();renderer.domElement.remove();host.classList.remove('scene-ready');button.hidden=true;pause.hidden=true;}
 media.addEventListener('change',dispose,{once:true});small.addEventListener('change',dispose,{once:true});renderer.domElement.addEventListener('webglcontextlost',dispose,{once:true});host.classList.add('scene-ready');sync();
}
