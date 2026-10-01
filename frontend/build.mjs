import { build } from 'esbuild';
import { mkdir, copyFile } from 'node:fs/promises';
const out='pratirodh/static';
await mkdir(`${out}/dist`,{recursive:true});
await mkdir(`${out}/fonts`,{recursive:true});
await mkdir(`${out}/licenses`,{recursive:true});
await build({entryPoints:['frontend/app.js','frontend/scene.js'],outdir:`${out}/dist`,bundle:true,splitting:true,format:'esm',minify:true,target:['es2020'],legalComments:'linked'});
for (const [name,weights] of [['space-grotesk',[400,500,600,700]],['ibm-plex-sans',[400,500,600]],['ibm-plex-mono',[400]]]) {
 for(const weight of weights) await copyFile(`node_modules/@fontsource/${name}/files/${name}-latin-${weight}-normal.woff2`,`${out}/fonts/${name}-${weight}.woff2`);
 await copyFile(`node_modules/@fontsource/${name}/LICENSE`,`${out}/licenses/${name}.txt`);
}
for (const name of ['three']) await copyFile(`node_modules/${name}/LICENSE`,`${out}/licenses/${name}.txt`);
