/*!
 * Adapted from React Bits Magnet and SpotlightCard, David Haz (c) 2026.
 * Source revision d86fccbd477786f94ca7eb891fbe0ec039d3cd3b.
 * MIT + Commons Clause: /static/licenses/react-bits.txt. Application integration only.
 * Native DOM/GSAP adaptation: bounded movement, no global pointer loop, keyboard resets.
 */
export function mountMagnet(link,gsap){
 const wrapper=document.createElement('span');wrapper.className='magnet-anchor';
 link.before(wrapper);wrapper.append(link);
 const xTo=gsap.quickTo(link,'x',{duration:.3,ease:'power3.out'});
 const yTo=gsap.quickTo(link,'y',{duration:.3,ease:'power3.out'});
 const reset=()=>{xTo(0);yTo(0);};
 const move=event=>{
  if(event.pointerType!=='mouse'||link.matches(':focus-visible'))return;
  const {left,top,width,height}=wrapper.getBoundingClientRect();
  const centerX=left+width/2,centerY=top+height/2;
  const offsetX=(event.clientX-centerX)/8,offsetY=(event.clientY-centerY)/8;
  xTo(Math.max(-6,Math.min(6,offsetX)));yTo(Math.max(-4,Math.min(4,offsetY)));
 };
 wrapper.addEventListener('pointermove',move);wrapper.addEventListener('pointerleave',reset);link.addEventListener('focus',reset);
 return ()=>{wrapper.removeEventListener('pointermove',move);wrapper.removeEventListener('pointerleave',reset);link.removeEventListener('focus',reset);gsap.killTweensOf(link);gsap.set(link,{clearProps:'transform'});wrapper.replaceWith(link);};
}
// SpotlightCard's soft Gaussian falloff, adapted to the existing evidence surfaces.
export function spotlightFalloff(color,softness=.7){
 const soft=Math.min(1,Math.max(0,softness));const core=(1-soft)**1.5*.85;
 const stop=(alpha,at)=>`color-mix(in srgb, ${color} ${(alpha*100).toFixed(2)}%, transparent) ${(at*100).toFixed(2)}%`;
 const list=[stop(1,0)];
 for(let i=0;i<=14;i++){const t=core+((1-core)*i)/14;const g=(t-core)/(1-core);const smooth=1-g*g*(3-2*g);const glow=Math.exp(-4.6*g*g)*(1-g**6);list.push(stop(smooth+(glow-smooth)*soft,t));}
 return list.join(', ');
}
