// Adapted from ThreeUI Constellation Field, @designcodeio/threeui 1.2.0.
// Copyright (c) 2026 Meng To. MIT: pratirodh/static/licenses/threeui.txt.
// https://threeui.com/backgrounds/constellation-field
// Seeded, bounded field; the scene owns time, pause, visibility and rendering.
export function createConstellation(canvas){
 const ctx=canvas.getContext('2d');
 let width=1,height=1,seed=1207;
 const random=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};
 const nodes=Array.from({length:38},()=>({x:random(),y:random(),vx:(random()-.5)*12,vy:(random()-.5)*12,r:random()*1.2+.7}));
 const bounce=(value,bound)=>{const wrapped=((value%(2*bound))+2*bound)%(2*bound);return wrapped>bound?2*bound-wrapped:wrapped;};
 return {
  resize(w,h,dpr){width=Math.max(1,w);height=Math.max(1,h);canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);ctx?.setTransform(dpr,0,0,dpr,0,0);},
  draw(time){
   if(!ctx)return;
   ctx.clearRect(0,0,width,height);
   const points=nodes.map(n=>({...n,x:bounce(n.x*width+n.vx*time,width),y:bounce(n.y*height+n.vy*time,height)}));
   ctx.strokeStyle=ctx.fillStyle='#9cdee2';ctx.lineWidth=.6;
   for(let i=0;i<points.length;i++)for(let j=i+1;j<points.length;j++){
    const a=points[i],b=points[j],distance=Math.hypot(a.x-b.x,a.y-b.y);
    if(distance<160){ctx.globalAlpha=(1-distance/160)*.19;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();}
   }
   for(const n of points){const pulse=.78+Math.sin(time+n.x)*.22;ctx.globalAlpha=pulse*.06;ctx.beginPath();ctx.arc(n.x,n.y,n.r*3,0,Math.PI*2);ctx.fill();ctx.globalAlpha=pulse*.38;ctx.beginPath();ctx.arc(n.x,n.y,n.r,0,Math.PI*2);ctx.fill();}
   ctx.globalAlpha=1;
  }
 };
}
