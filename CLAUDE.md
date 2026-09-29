# cookie-plug

Lead-generation engine and playbooks for a co-packing referral partnership (cookies, baked goods, pet treats, pet food). Read `README.md` first, then `docs/PINS.md` for what is waiting on the owner.

## Working here

- Python 3.11, `src/` layout, package `leadgen`, CLI entry point `leadgen` (`pip install -e .`).
- Run `python -m pytest --cov=leadgen` before every commit; coverage must stay above 80 percent (it is about 97). Tests are offline: HTTP goes through `httpx.MockTransport`, the Anthropic client is a fake object with a `messages` attribute.
- Claude calls use the official `anthropic` SDK, model `claude-opus-5` by default, structured outputs via `client.messages.parse(..., output_format=Model)`, web research via the `web_search_20260209` server tool with `pause_turn` continuation (see `src/leadgen/dossier.py`). Never add another provider.
- Every function has a docstring and type hints; keep functions under 50 lines; classes implement `__repr__`; no mutable default arguments.
- Facility facts live only in `config/facility.yaml`. Anything marked `TO_CONFIRM` must never appear in outreach text or prompts as a claim.
- Hand-verified lead facts go in `leads/overrides.csv`, never edited into `seed_list.csv`; rebuild with `scripts/build_seed_list.py`.
- Commit messages describe the change and end with the attribution lines the session provides. Do not put model identifiers in commits, PRs, or code.

## Layout

`src/leadgen/`: models, facility, discover (CSV), htmlimport (saved pages), sources and triggers (public feeds), enrich (websites), scoring, ai (qualify/draft), dossier (web research), outreach (sequences), schedule (due touches), contacts (email candidates), crm (SQLite), economics, cli.
`config/`: facility, ICP weights, feeds, sequence templates. `prompts/`: system prompts. `docs/`: strategy, playbooks, pins, decisions. `leads/`: committed research outputs. `scripts/`: weekly pipeline, seed-list build, DNS check.
