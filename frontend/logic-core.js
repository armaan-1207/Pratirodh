// Adapted from ThreeUI Logic Core, @designcodeio/threeui 1.2.0.
// Copyright (c) 2026 Meng To. MIT: pratirodh/static/licenses/threeui.txt.
// https://threeui.com/three-js/structure-flow/logic-core
// Local module, seeded node layout, shared render lifecycle, no CDN/iframe.
export function createLogicCore(THREE, scene){
 let seed=1207;
 function random(){seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;}
            const group = new THREE.Group();
            scene.add(group);

            // Material Definitions
            const basePlatformMat = new THREE.MeshStandardMaterial({ color: 0x17262a, roughness: 0.9, metalness: 0.1 });
            const coreEmissiveMat = new THREE.MeshStandardMaterial({ color: 0x9cdee2, emissive: 0x9cdee2, emissiveIntensity: 0.5, roughness: 0.2 });
            const wireframeMat = new THREE.LineBasicMaterial({ color: 0x6d929b, transparent: true, opacity: 0.4 });

            // A wider original security landscape surrounds the ThreeUI core.
            // Shared geometry/materials keep this full-bleed world inexpensive.
            const landscape=new THREE.Group();scene.add(landscape);
            const towerGeo=new THREE.BoxGeometry(1.1,1,1.1),towerMat=new THREE.MeshStandardMaterial({color:0x1e353b,roughness:.75,metalness:.25});
            const towerEdges=new THREE.EdgesGeometry(towerGeo),edgeMat=new THREE.LineBasicMaterial({color:0x547b84,transparent:true,opacity:.22});
            for(let i=0;i<44;i++){
                const angle=random()*Math.PI*2,radius=14+random()*18,height=1+random()*6;
                const tower=new THREE.Mesh(towerGeo,towerMat);tower.position.set(Math.cos(angle)*radius,-2+height/2,Math.sin(angle)*radius);tower.scale.y=height;tower.add(new THREE.LineSegments(towerEdges,edgeMat));landscape.add(tower);
            }
            const floor=new THREE.GridHelper(90,60,0x355d65,0x243e45);floor.position.y=-2.3;floor.material.transparent=true;floor.material.opacity=.24;landscape.add(floor);

            // Geometry Build: Base Platform
            const platformGeo = new THREE.BoxGeometry(16, 0.5, 16);
            const platform = new THREE.Mesh(platformGeo, basePlatformMat);
            platform.position.y = -2;
            group.add(platform);

            // Inset technical grid and containment rings ground the floating core.
            const grid = new THREE.GridHelper(15.5, 16, 0x547b83, 0x345159);
            grid.position.y = -1.73;
            grid.material.transparent = true;
            grid.material.opacity = 0.35;
            group.add(grid);
            const rings=[];
            for (const radius of [3,5.5]) {
                const ring = new THREE.Mesh(new THREE.TorusGeometry(radius,.025,6,80), new THREE.MeshBasicMaterial({color:0x9cdee2,transparent:true,opacity:.32}));
                ring.rotation.x=Math.PI/2;ring.position.y=-1.68;group.add(ring);rings.push(ring);
            }

            const platformEdges = new THREE.LineSegments(new THREE.EdgesGeometry(platformGeo), wireframeMat);
            platform.add(platformEdges);

            // Geometry Build: Central Logic Core
            const coreGeo = new THREE.BoxGeometry(2, 4, 2);
            const core = new THREE.Mesh(coreGeo, coreEmissiveMat);
            core.position.y = 0.25;
            group.add(core);

            // Geometry Build: Orbiting Data Nodes
            const nodes = [];
            const nodeCount = 12;
            for(let i = 0; i < nodeCount; i++) {
                const isAccent = random() > 0.7;
                const nodeMat = isAccent ? coreEmissiveMat : new THREE.MeshStandardMaterial({ color: 0x344b51, roughness: 0.8 });
                const size = 0.4 + random() * 0.4;
                const nodeGeo = new THREE.BoxGeometry(size, size, size);
                const node = new THREE.Mesh(nodeGeo, nodeMat);

                const angle = (i / nodeCount) * Math.PI * 2;
                const radius = 4 + random() * 4;

                node.position.set(Math.cos(angle) * radius, -1 + random() * 4, Math.sin(angle) * radius);

                // Add tiny wireframe to nodes for technical look
                node.add(new THREE.LineSegments(new THREE.EdgesGeometry(nodeGeo), new THREE.LineBasicMaterial({ color: 0x555555, transparent: true, opacity: 0.3 })));

                node.userData = {
                    angle,
                    radius,
                    speed: 0.005 + random() * 0.015,
                    yBase: node.position.y,
                    yOffset: random() * Math.PI * 2
                };
                group.add(node);
                nodes.push({ mesh: node, isAccent });
            }

            // Lighting Setup
            scene.add(new THREE.AmbientLight(0xffffff, 0.3));

            const dirLight = new THREE.DirectionalLight(0xffffff, 0.6);
            dirLight.position.set(10, 20, 5);
            scene.add(dirLight);

            const pointLight = new THREE.PointLight(0x9cdee2, 1.5, 25);
            pointLight.position.set(0, 1, 0);
            scene.add(pointLight);


 return {group, core, material:coreEmissiveMat, update(time){
  group.position.y=Math.sin(time*.5)*.2;
  coreEmissiveMat.emissiveIntensity=.45+(Math.sin(time*2.5)+1)*.25;
  rings.forEach((ring,i)=>{ring.material.opacity=.18+(Math.sin(time*1.2-i)+1)*.12;});
  nodes.forEach(({mesh})=>{const data=mesh.userData;const angle=data.angle+time*data.speed*30;mesh.position.x=Math.cos(angle)*data.radius;mesh.position.z=Math.sin(angle)*data.radius;mesh.position.y=data.yBase+Math.sin(time*1.5+data.yOffset)*.5;mesh.rotation.set(time*.35,time*.5,0);});
 }};
}
