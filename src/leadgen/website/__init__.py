"""Static website generator for the inbound side of the pipeline.

The site is built from three kinds of input, none of which is code:
``site/config.yaml`` (brand, domain, contact details), ``config/facility.yaml``
(facility facts, rendered only once confirmed), and ``site/content/``
(guides, FAQ, category copy). ``site/templates/`` holds the Jinja layouts.

Three build modes share one set of templates:

* production: multi-page site in ``site/dist/``; refuses placeholders.
* draft: the same pages with placeholders highlighted and ``noindex``.
* preview: one self-contained HTML fragment with hash routing, for review.

Jinja2 and Markdown are imported lazily so the rest of ``leadgen`` never
needs them.
"""
