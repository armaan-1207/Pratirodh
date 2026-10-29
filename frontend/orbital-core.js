import {surfaceNoise} from './surface-noise.js';
// Original PRATIRODH sculpture. Three.js procedural geometry and studio lighting.
// Material/composition reference: Codrops Animated Displaced Sphere (Pavel Mazhuga).
// Includes MIT-licensed Perlin noise from Codrops / Stefan Gustavson. No remote assets.
export function createOrbitalCore(THREE,scene){
 const group=new THREE.Group();scene.add(group);
 const geometry=new THREE.TorusKnotGeometry(2.65,.74,224,28,2,3);
 const material=new THREE.MeshPhysicalMaterial({color:0x8aa6af,metalness:.96,roughness:.24,clearcoat:.65,clearcoatRoughness:.16,envMapIntensity:1.8});
 const clock={value:0};
 material.onBeforeCompile=shader=>{shader.uniforms.uSurfaceTime=clock;shader.vertexShader='uniform float uSurfaceTime;\n'+surfaceNoise+shader.vertexShader;shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','vec3 transformed = position + normal * (0.08 * cnoise(position * 2.0 + vec3(uSurfaceTime * 0.13)));');};
 const sculpture=new THREE.Mesh(geometry,material);sculpture.rotation.set(.3,.2,-.4);group.add(sculpture);
 const seam=new THREE.Mesh(new THREE.TorusKnotGeometry(2.66,.745,144,8,2,3),new THREE.MeshBasicMaterial({color:0x9cdee2,wireframe:true,transparent:true,opacity:.045}));seam.rotation.copy(sculpture.rotation);group.add(seam);
 const orbits=[];
 for(let i=0;i<3;i++){
  const points=[],r=4.2+i*.45;
  for(let j=0;j<=128;j++){const a=j/128*Math.PI*2;points.push(new THREE.Vector3(Math.cos(a)*r,Math.sin(a)*r,0));}
  const orbit=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),new THREE.LineBasicMaterial({color:0x85bbc9,transparent:true,opacity:.22-i*.04}));
  orbit.rotation.set(.8+i*.6,.3+i*.7,i*.4);group.add(orbit);
  const node=new THREE.Mesh(new THREE.SphereGeometry(.035,8,6),new THREE.MeshBasicMaterial({color:0xd7f5f9}));orbit.add(node);orbits.push({node,r});
 }
 scene.add(new THREE.HemisphereLight(0xc6eaf2,0x101c26,1.3));
 const key=new THREE.DirectionalLight(0xe6fffc,4);key.position.set(3,7,5);scene.add(key);
 const rim=new THREE.DirectionalLight(0x519aaa,3);rim.position.set(-5,-2,-3);scene.add(rim);
 const warm=new THREE.DirectionalLight(0xdbc9b0,2);warm.position.set(6,0,-4);scene.add(warm);
 return {group,update(time,progress=0){
  clock.value=time;
  sculpture.rotation.y=time*.12+progress*1.4;sculpture.rotation.z=-.4+progress*.65;seam.rotation.copy(sculpture.rotation);
  group.scale.setScalar(1+progress*.22);
  orbits.forEach(({node,r},i)=>{const a=time*(.17+i*.04)+i*1.7;node.position.set(Math.cos(a)*r,Math.sin(a)*r,0);});
 }};
}
