# Frontend design and attribution

PRATIRODH keeps Flask/Jinja, local assets, its brand mark, Outfit display, Space Grotesk brand, and IBM Plex body fonts, and the existing protected execution routes.

## Design references used

- **ThreeUI Logic Core:** https://threeui.com/three-js/structure-flow/logic-core. The isometric platform, central core, orbital nodes, materials, and lighting in `frontend/logic-core.js` are adapted from the public `@designcodeio/threeui` 1.2.0 `platform-core.html.js` source. Copyright (c) 2026 Meng To, MIT. The complete license is retained at `pratirodh/static/licenses/threeui.txt`. The adaptation uses the existing Three.js bundle, a seeded layout, PRATIRODH colors, an owned render lifecycle, and local imports. It removes the original CDN scripts, fonts, surrounding marketing page, and iframe requirement.
- **21st.dev Animated Tabs by Julien Thibeaut / Motion Primitives:** https://21st.dev/@ibelick/components/animated-tabs. The moving active selection surface and short content transition inform the example selector. The behavior is implemented in native DOM/GSAP against the existing keyboard-accessible tabs rather than embedding the React component. The preview identifies the reference as MIT. No copied React source or external runtime is required.
- **Taste Skill:** https://github.com/Leonxlnx/taste-skill/tree/main/skills/taste-skill. Applied its audit-first redesign, wider typography, restrained copy, layout variation, color consistency, and purposeful motion guidance. The established dark security-lab brief is preserved.
- **GPT Taste:** https://github.com/Leonxlnx/taste-skill/tree/main/skills/gpt-tasteskill. Applied its editorial split hero, two-line headline, horizontal workflow accordion, generous chapter spacing, scroll-linked text reveal, and stacked evidence cards. The requested redesign retains the dark cyan brand and protected Flask routes. The deterministic layout selection used seed 20. Outfit replaces the selected Cabinet Grotesk because the latter package license prohibits redistribution through repositories. Imagery uses the actual ThreeUI artwork and brand mark instead of unrelated stock photographs.
- **Kage composition reference:** https://threeui.com/landing-pages/kage.html. Reviewed the first-party source bundle and live hero. The full-viewport artwork, foreground wordmark, and layered composition informed the final hero. PRATIRODH uses an original security landscape around its adapted Logic Core; no Kage temple, moon, vegetation, images, source scene, or React wrapper is embedded.
- **GSAP / ScrollTrigger:** locally bundled hero entry, section reveals, tab feedback, scrubbed question text, stacked evidence cards, and illustrated challenge sequence.

## Motion and accessibility

The core is an explanatory illustration, with a caption outside the artwork. Its phases describe the illustrative challenge sequence and do not represent backend execution. Pause stops both the scene timeline and render loop. The artwork pauses off-screen and in hidden tabs. Reduced motion, mobile screens, and unavailable WebGL retain the static security-flow diagram. All primary controls work independently of the artwork.

## Content organization

The showcase explains discovery, candidate repair, verification, and signed review. Recorded synthetic verification metrics are explicitly labeled. Detailed upstream campaign status stays available in a disclosure on Validation and in the machine-readable status endpoint. Original outcomes and backend decisions are preserved.

## Desktop verification

Desktop layout checked at 1440 pixels: the hero heading occupies two lines, CTAs fit on screen, and page scroll width matches client width. Accordion expansion works by click and Enter, example tabs keep keyboard navigation, and browser warning/error logs are empty. Paused core canvas captures are byte-identical. The backdrop also stops when the illustration is paused, offscreen, or the document is hidden. The final desktop pass intentionally skips further mobile review at the user's request. No Lighthouse score is claimed; the current browser tool does not expose a Lighthouse audit.
