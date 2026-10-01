# Interface sources and third party notices

The interface is an original Flask/Jinja, CSS and JavaScript implementation. No paid template code was copied.

- ThreeUI Agent AI presentation: https://threeui.com/landing-pages/agent-ai-landing-page — reference for technical depth and sequential 3D storytelling.
- Taste redesign guidance: https://raw.githubusercontent.com/Leonxlnx/taste-skill/main/skills/redesign-skill/SKILL.md — typography, hierarchy, progressive enhancement and interaction-state audit.
- 21st.dev: https://21st.dev/ — inspiration for tabbed controls, navigation and evidence-panel composition; no third-party component source incorporated.
- GSAP 3.15.0: https://gsap.com/ — actual reveal and diagram transitions. Standard No Charge license retained in pratirodh/static/licenses/gsap.txt; not represented as MIT.
- Three.js: actual original verification scene. MIT license retained in pratirodh/static/licenses/three.txt.
- Space Grotesk, IBM Plex Sans and IBM Plex Mono: self-hosted Latin WOFF2 subsets from pinned Fontsource packages; SIL Open Font License texts retained in pratirodh/static/licenses/.
- esbuild: build-time bundler, MIT; package lock pins the complete dependency graph.

Run `npm ci` followed by `npm run build` to reproduce browser bundles and font files. Checked-in output under pratirodh/static/dist is deployed by Flask and packaged in Python distributions. Node and npm are setup/build dependencies only. The browser never contacts these reference sites or a CDN. Preserve the local license files and generated legal notices when redistributing.
