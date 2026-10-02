# Design references

Saved at the 2026-10-02 session handoff so nothing lives only in a container.

- `mockups/*.html`: the standalone home-page layout mockups the owner reviewed on 2026-09-30, one per option. Four became site skins (`open-book` for bakery, `open-signal` for pet, `blueprint` for formulation, `night-shift` for pet formulation; see `site/themes/`). Carton label, form-first, photo magazine, and schedule board were never built. Their wording ("No waitlist", dated status lines) is placeholder text, not confirmed facility facts. They load Google Fonts and inline scripts, which is fine here but never under `site/`.
- `mockups/project/`: the design-canvas export of options A to C. It needs a `support.js` that was not saved, so it does not open on its own; the published link in `docs/HANDOFF.md` still works.
- `guide_style_checker.py`: an archived checker for the guides' house style (length limits, sources, no dashes or exclamation marks). Out of date; see its header.

Published versions of every mockup are listed in `docs/HANDOFF.md`.
