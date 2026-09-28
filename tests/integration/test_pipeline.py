"""End-to-end pipeline: import -> enrich (mocked web) -> score -> qualify -> draft -> store -> report."""

import httpx

from leadgen.ai import RuleBasedQualifier
from leadgen.crm import LeadStore
from leadgen.discover import import_csv
from leadgen.enrich import WebsiteEnricher
from leadgen.models import Stage
from leadgen.outreach import render_sequence
from leadgen.scoring import apply_score


def test_full_pipeline(tmp_path, sample_csv, shopify_html, facility, weights, sender, sequence_template, monkeypatch):
    monkeypatch.chdir(tmp_path.parent)

    def handler(request: httpx.Request) -> httpx.Response:
        if "barkery" in request.url.host:
            return httpx.Response(200, text="<html><title>Barkery Lane</title><body>Dog treats. Wholesale available.</body></html>")
        if request.url.path == "/products.json":
            return httpx.Response(200, json={"products": [{"variants": [{"available": False}]}] * 25})
        return httpx.Response(200, text=shopify_html)

    enricher = WebsiteEnricher(client=httpx.Client(transport=httpx.MockTransport(handler)))
    report = import_csv(sample_csv)
    assert len(report.leads) == 2

    with LeadStore(tmp_path / "pipeline.sqlite3") as store:
        for lead in report.leads:
            enricher.enrich(lead)
            apply_score(lead, weights, facility)
            assessment = RuleBasedQualifier().assess(lead, facility)
            if assessment.fit_score >= 55:
                lead.stage = Stage.QUALIFIED
            store.upsert(lead)

        ranked = store.list()
        assert ranked[0].company == "Crumb Co"
        assert ranked[0].score > ranked[1].score
        assert ranked[0].stage == Stage.QUALIFIED
        assert ranked[0].signals.product_count == 25

        touches = render_sequence(ranked[0], facility, sender, sequence_template)
        assert "Whole Foods" in touches[0].body

        store.advance("crumbco.com", Stage.CONTACTED)
        store.advance("crumbco.com", Stage.REPLIED, note="asked for capabilities sheet")
        funnel = store.pipeline_report()
        assert funnel["replied"] == 1
        assert len(store.activities("crumbco.com")) == 2
