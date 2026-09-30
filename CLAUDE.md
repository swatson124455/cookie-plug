# cookie-plug

Lead-generation engine and playbooks for a co-packing referral partnership (cookies, baked goods, pet treats, pet food). Read `README.md` first, then `docs/PINS.md` for what is waiting on the owner.

## Working here

- Python 3.11, `src/` layout, package `leadgen`, CLI entry point `leadgen` (`pip install -e .`).
- Run `python -m pytest --cov=leadgen` before every commit; coverage must stay above 80 percent (it is about 97). Tests are offline: HTTP goes through `httpx.MockTransport`, the Anthropic client is a fake object with a `messages` attribute.
- Claude calls use the official `anthropic` SDK, model `claude-opus-5` by default, structured outputs via `client.messages.parse(..., output_format=Model)`, web research via the `web_search_20260209` server tool with `pause_turn` continuation (see `src/leadgen/dossier.py`). Never add another provider.
- Every function has a docstring and type hints; keep functions under 50 lines; classes implement `__repr__`; no mutable default arguments.
- Facility facts live only in `config/facility.yaml`. Anything marked `TO_CONFIRM` must never appear in outreach text, prompts, or site pages as a claim. Outreach templates get speed claims only through `{speed_line}`/`{speed_short}`, which state a number once `sampling_turnaround_days` is confirmed.
- Text from outside (web forms, feeds, lead notes, scraped pages) goes into a Claude prompt only through `leadgen.prompting.fenced`, and the system prompt carries `UNTRUSTED_NOTICE`.
- The website: code in `src/leadgen/website/`, copy in `site/content/`, layouts in `site/templates/`, settings in `site/config.yaml`. `python site/build.py` (production, refuses placeholders), `--draft`, `--preview FILE`, `--images` (commit the PNGs), `--indexnow` (after a deploy). Ad landing pages live in `site/content/landing.yaml` (noindex, `/lp/`). Guide front matter and upkeep are in `docs/17` section 11. The live site ships no JavaScript and a strict CSP: no inline `style` attributes in templates.
- Hand-verified lead facts go in `leads/overrides.csv`, never edited into `seed_list.csv`; rebuild with `scripts/build_seed_list.py`.
- Commit messages describe the change and end with the attribution lines the session provides. Do not put model identifiers in commits, PRs, or code.

## Layout

`src/leadgen/`: models, facility, discover (CSV), htmlimport (saved pages), inbound (website form submissions, CSV or Netlify API), sources and triggers (public feeds), enrich (websites), scoring, ai (qualify/draft), prompting (fencing outside text), dossier (web research), outreach (sequences), schedule (due touches), contacts (email candidates), crm (SQLite), economics, website (static site generator), cli.
`config/`: facility, ICP weights, feeds, sequence templates. `prompts/`: system prompts. `site/`: website content, templates, static files, config, build wrapper. `docs/`: strategy, playbooks, pins, decisions. `leads/`: committed research outputs. `scripts/`: weekly pipeline, seed-list build, DNS check.
