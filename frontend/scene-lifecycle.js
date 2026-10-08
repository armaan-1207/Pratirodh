// Keep animation eligibility live when the sidebar or window changes width.
export function watchContext(canvas, onLoss, onRestore) {
 const lost = event => { event.preventDefault(); onLoss(); };
 canvas.addEventListener('webglcontextlost', lost);
 canvas.addEventListener('webglcontextrestored', onRestore);
 return () => {
  canvas.removeEventListener('webglcontextlost', lost);
  canvas.removeEventListener('webglcontextrestored', onRestore);
 };
}

export function watchScene(host, loadScene = () => import('./scene.js')) {
 const reduced = matchMedia('(prefers-reduced-motion: reduce)');
 let visible = false, pending = false, disposed = false, cleanup = null;
 async function sync() {
  if (disposed) return;
  if (reduced.matches) {
   cleanup?.(); cleanup = null; return;
  }
  if (!visible || cleanup || pending) return;
  pending = true;
  try {
   const {mountScene} = await loadScene();
   if (!disposed && visible && !reduced.matches && !cleanup)
    cleanup = mountScene(host) || null;
  } catch {
   // A usable static diagram remains when WebGL or the module is unavailable.
  } finally { pending = false; }
 }
 const observer = new IntersectionObserver(entries => {
  visible = entries.some(entry => entry.isIntersecting);
  return sync();
 }, {rootMargin:'100px'});
 observer.observe(host);
 reduced.addEventListener('change', sync);
 return () => {
  disposed = true;
  observer.disconnect();
  reduced.removeEventListener('change', sync);
  cleanup?.(); cleanup = null;
 };
}
