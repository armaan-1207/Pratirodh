# Frontend design and attribution

## Current hero restoration — 10 October 2026

Restored the previously verified ThreeUI Logic Core cube/landscape scene and left-aligned charcoal/cyan composition from candidate `9923424`. The newer Every patch / Put to the test headline, introductory content and Open workspace action remain. Mobile animation, reduced-motion fallback, offscreen/background suspension and WebGL context restoration remain. Other product pages and backend behavior are retained. Earlier orbital source and notices are preserved as historical work; the rebuilt active scene uses the cube module.


## Historical local redesign — 9 October 2026

The 9 October uncommitted interface used a centered two-line hero, an original metallic Three.js knot, the restored charcoal/cyan palette (`#101416` / `#9cdee2`), Outfit display typography, shared product controls and evidence layouts. The sculpture is conceptual artwork, not a backend progress indicator. On 10 October, the user requested restoration of the cube/landscape hero. The latest product controls and evidence layouts are retained.

Actual free-source reuse:

- **Codrops displaced-sphere shader:** Perlin displacement functions adapted from Pavel Mazhuga's [tutorial repository](https://github.com/pavel-mazhuga/codrops-tutorial-distorted-sphere-custom-material), revision `83bb3d2639460e4a5c478e23414356957968a8d8`. `frontend/surface-noise.js` is used in our original torus-knot material. Codrops and Stefan Gustavson MIT notices are retained in `static/licenses/codrops-sphere.txt` and `webgl-noise.txt`.
- **React Bits Magnet and SpotlightCard:** interaction geometry and soft falloff adapted into native DOM/GSAP in `frontend/react-bits-interactions.js`, from [React Bits](https://github.com/DavidHDev/react-bits), revision `d86fccbd477786f94ca7eb891fbe0ec039d3cd3b`. Used as part of this application, not redistributed as a component library. The complete **MIT + Commons Clause** notice is retained in `static/licenses/react-bits.txt`; these adaptations are not relicensed under the project's plain MIT license. Magnetic movement is bounded to six pixels horizontally/four vertically, disabled for coarse pointers and reduced motion, and reset for keyboard focus.
- **Lenis 1.3.26:** actual MIT library, pinned in the npm lockfile and bundled locally. Uses the existing GSAP ticker on the editorial homepage; form/evidence pages use native scrolling. Native touch and reduced-motion behavior are preserved. Notice: `static/licenses/lenis.txt`.
- **Three.js RoomEnvironment:** procedural studio lighting, with no external HDRI, image service or CDN.

[ThreeUI Agent AI](https://threeui.com/landing-pages/agent-ai-landing-page), [21st.dev](https://21st.dev/@ibelick/components/animated-tabs), [Scrolltide](https://www.scrolltide.co/) and [Interactive 3D Particle Morphing](https://geeai.github.io/Interactive-3D-Particle-Morphing/) were reviewed as composition/motion references. No premium template source or assets were copied. React and another UI framework were not added.

The shared system covers Overview, Projects, Workspace, Comparison, Validation, Walkthrough and result/job templates. Workspace places runtime status and the local-model form before expandable supplied-repair demonstrations. Historical evidence remains inspectable, with explicit stale-status filtering and recovery guidance. Protected execution routes, decisions, signatures and source freshness have not been relaxed for presentation.

The current artwork uses one render loop, pauses offscreen/background, recovers after context restoration, and animates on narrow screens. Reduced motion or unavailable WebGL uses the static diagram. Scroll-linked sculpture movement, headline fading, evidence stacking and keyboard-accessible example tabs remain locally bundled. Seven frontend lifecycle tests pass. Full Docker-enabled Python verification passed 456 tests with zero skips before the final presentation-only refinements; affected web checks are rerun separately.

Browser review has observed the current narrow 570-pixel and desktop 1340-pixel layouts. The browser viewport override did not change the observed page dimensions; 360/390/tablet emulation and physical-phone performance are not claimed by this review. Historical checks below belong to earlier revisions.

## Historical design record (retained)


PRATIRODH keeps Flask/Jinja, local assets, its brand mark, Outfit display, Space Grotesk brand, and IBM Plex body fonts, and the existing protected execution routes.

## Design references used

- **ThreeUI Logic Core:** https://threeui.com/three-js/structure-flow/logic-core. The isometric platform, central core, orbital nodes, materials, and lighting in `frontend/logic-core.js` are adapted from the public `@designcodeio/threeui` 1.2.0 `platform-core.html.js` source. Copyright (c) 2026 Meng To, MIT. The complete license is retained at `pratirodh/static/licenses/threeui.txt`. The adaptation uses the existing Three.js bundle, a seeded layout, PRATIRODH colors, an owned render lifecycle, and local imports. It removes the original CDN scripts, fonts, surrounding marketing page, and iframe requirement.
- **21st.dev Animated Tabs by Julien Thibeaut / Motion Primitives:** https://21st.dev/@ibelick/components/animated-tabs. The moving active selection surface and short content transition inform the example selector. The behavior is implemented in native DOM/GSAP against the existing keyboard-accessible tabs rather than embedding the React component. The preview identifies the reference as MIT. No copied React source or external runtime is required.
- **Taste Skill:** https://github.com/Leonxlnx/taste-skill/tree/main/skills/taste-skill. Applied its audit-first redesign, wider typography, restrained copy, layout variation, color consistency, and purposeful motion guidance. The established dark security-lab brief is preserved.
- **GPT Taste:** https://github.com/Leonxlnx/taste-skill/tree/main/skills/gpt-tasteskill. Applied its editorial split hero, two-line headline, horizontal workflow accordion, generous chapter spacing, scroll-linked text reveal, and stacked evidence cards. The requested redesign retains the dark cyan brand and protected Flask routes. The deterministic layout selection used seed 20. Outfit replaces the selected Cabinet Grotesk because the latter package license prohibits redistribution through repositories. Imagery uses the actual ThreeUI artwork and brand mark instead of unrelated stock photographs.
- **Kage composition reference:** https://threeui.com/landing-pages/kage.html. Reviewed the first-party source bundle and live hero. The full-viewport artwork, foreground wordmark, and layered composition informed the final hero. PRATIRODH uses an original security landscape around its adapted Logic Core; no Kage temple, moon, vegetation, images, source scene, or React wrapper is embedded.
- **GSAP / ScrollTrigger:** locally bundled hero entry, section reveals, tab feedback, scrubbed question text, stacked evidence cards, and illustrated challenge sequence.

## Motion and accessibility

The second desktop polish pass adds the ThreeUI Constellation Field from the same MIT 1.2.0 source bundle (`constellation-field.html.js`): https://threeui.com/backgrounds/constellation-field. Its particle/link canvas uses 38 seeded nodes and the scene's existing render loop and timeline, so pause and visibility controls cover both layers. The original gold palette, CDN scripts, marketing markup and independent animation loop are removed. Evidence panel pointer lighting follows the public 21st.dev / Motion Primitives Spotlight pattern: https://21st.dev/@ibelick/components/spotlight. This is a native CSS/DOM adaptation, with a static keyboard focus edge and no extra animation loop or React runtime.

The current core is an explanatory illustration, with a caption outside the artwork. Its phases describe the illustrative challenge sequence and do not represent backend execution. It animates continuously while visible; pause and angle controls have been removed. The artwork stops off-screen and in hidden tabs. Reduced motion, mobile screens, and unavailable WebGL retain the static security-flow diagram. All primary controls work independently of the artwork. Pause-control observations below describe the earlier design checkpoint.

## Content organization

The follow-up component review also covered ThreeUI Text Path Studies / Globe Study, Glass AI Button, Gallery Heading, and the public Diagnostics Panel and Launch Button sources. The homepage takes the masked line-reveal idea from Diagnostics Panel and button depth/pressed feedback from Launch Button, implemented with the existing GSAP and native link. Their unrelated copy, imagery, colors and extra runtimes are not embedded. The large globe and galaxy button remain references rather than additional competing hero scenes. Reduced motion leaves the headline immediately readable.

The showcase explains discovery, candidate repair, verification, and signed review. Recorded synthetic verification metrics are explicitly labeled. Detailed upstream campaign status stays available in a disclosure on Validation and in the machine-readable status endpoint. Original outcomes and backend decisions are preserved.

## Desktop verification

Desktop layout checked at 1440 pixels: the hero heading occupies two lines, CTAs fit on screen, and page scroll width matches client width. Accordion expansion works by click and Enter, example tabs keep keyboard navigation, and browser warning/error logs are empty. The follow-up desktop pass at 1295 pixels also has two headline lines and no horizontal overflow. Paused screenshots covering both the core and constellation canvas are byte-identical; evidence panel pointer lighting, example tab selection, and an empty warning/error log were checked. The backdrop also stops when the illustration is paused, offscreen, or the document is hidden. The final desktop pass intentionally skips further mobile review at the user's request. No Lighthouse score is claimed; the current browser tool does not expose a Lighthouse audit.
