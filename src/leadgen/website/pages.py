"""The page registry: every route on the site, its template, metadata, and structured data.

Pages are plain records. Rendering and writing happen in ``leadgen.website.build``;
this module only decides what exists, what each page is called, and what
JSON-LD describes it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Any

from leadgen.website import seo

if TYPE_CHECKING:
    from leadgen.website.render import SiteContext

TITLE_LIMIT = 65


@dataclass
class Page:
    """One route: where it lives, how it renders, and how it describes itself to machines."""

    key: str
    template: str
    title: str
    description: str
    nav: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    nodes: list[dict[str, Any]] = field(default_factory=list)
    og_image: str = "og/default.png"
    noindex: bool = False
    in_sitemap: bool = True
    lastmod: date | None = None
    crumbs: list[tuple[str, str]] = field(default_factory=list)

    @property
    def output_path(self) -> str:
        """File path inside dist (``index.html``, ``faq/index.html``, ``404.html``)."""
        if self.key == "404":
            return "404.html"
        return f"{self.key}/index.html" if self.key else "index.html"

    def __repr__(self) -> str:
        return f"Page(key={self.key!r}, template={self.template!r})"


def titled(site: "SiteContext", title: str) -> str:
    """Append the short brand when it fits in a search result title."""
    suffixed = f"{title} | {site.cfg.short_name}"
    return suffixed if len(suffixed) <= TITLE_LIMIT else title


def _crumb_nodes(site: "SiteContext", page: Page) -> list[dict[str, Any]]:
    """Breadcrumb JSON-LD for inner pages."""
    if not page.crumbs:
        return []
    trail = [("Home", site.abs_url(""))] + [(name, site.abs_url(key)) for name, key in page.crumbs]
    return [seo.breadcrumb_node(trail, site.abs_url(page.key))]


def structured_data(site: "SiteContext", page: Page) -> dict[str, Any]:
    """The page's single JSON-LD graph: organization, site, author, and page nodes."""
    nodes = [seo.organization_node(site.cfg), seo.website_node(site.cfg)]
    if site.real(site.cfg.contact.name):
        nodes.append(seo.person_node(site.cfg))
    return seo.graph(nodes + page.nodes + _crumb_nodes(site, page))


def home_page(site: "SiteContext") -> Page:
    """The front door: capacity status, who it is for, the steps, and the form."""
    url = site.abs_url("")
    description = ("Open co-packing lines for cookies, baked goods, pet treats, and pet food. Turnkey from formulation "
                   "to shelf-ready case packs. Check capacity for your product.")
    service = seo.service_node(site.cfg, "Co-packing for cookie, bakery, pet-treat, and pet-food brands", description, url)
    return Page("", "home.html", titled(site, "Co-Packer With Open Capacity"), description, nav="home",
                nodes=[service, seo.faq_node([q for q in site.faq if q.featured], url)])


def capabilities_page(site: "SiteContext") -> Page:
    """Confirmed lines, services, certifications, and numbers."""
    return Page("capabilities", "capabilities.html", titled(site, "Capabilities: Lines, Services, Certifications"),
                "What the facility we represent makes and handles, limited to facts it has confirmed in writing: "
                "production lines, turnkey services, and certifications.", nav="capabilities",
                crumbs=[("Capabilities", "capabilities")])


def category_pages(site: "SiteContext") -> list[Page]:
    """One landing page per production line, from ``site/content/categories.yaml``."""
    pages: list[Page] = []
    for slug, spec in site.categories.items():
        url = site.abs_url(slug)
        nodes = [seo.service_node(site.cfg, spec["h1"], spec["description"], url)]
        if spec["questions"]:
            nodes.append(seo.faq_node(spec["questions"], url))
        pages.append(Page(slug, "category.html", titled(site, spec["title"]), spec["description"], nav="capabilities",
                          context={"spec": spec, "line": site.line(spec["line"])}, nodes=nodes,
                          og_image=site.og_image(f"og/{slug}.png"), crumbs=[(spec["crumb"], slug)]))
    return pages


def guide_pages(site: "SiteContext") -> list[Page]:
    """The guides index and one page per guide."""
    index = Page("guides", "guides.html", titled(site, "Co-Packer Guides for Food and Pet Brands"),
                 "Plain answers for founders: how to find and qualify a co-packer, minimums and costs, retailer "
                 "requirements, shelf-stable reformulation, and second sourcing.", nav="guides",
                 crumbs=[("Guides", "guides")])
    pages = [index]
    for guide in site.guides:
        key = f"guides/{guide.slug}"
        image = site.og_image(f"og/guides/{guide.slug}.png")
        pages.append(Page(key, "guide.html", titled(site, guide.seo_title or guide.title), guide.description, nav="guides",
                          context={"guide": guide}, og_image=image, lastmod=guide.updated,
                          nodes=[seo.article_node(site.cfg, guide, site.abs_url(key), site.abs_asset(image))],
                          crumbs=[("Guides", "guides"), (guide.short_title, key)]))
    return pages


def company_pages(site: "SiteContext") -> list[Page]:
    """FAQ, about, contact, privacy, and the two utility pages."""
    faq_url = site.abs_url("faq")
    return [
        Page("faq", "faq.html", titled(site, "Co-Packer FAQ: Minimums, Samples, Costs"),
             "Straight answers on co-packer minimums, sampling, certifications, private label, pet products, "
             "costs, and how working with us works.", nav="faq", nodes=[seo.faq_node(site.faq, faq_url)],
             crumbs=[("FAQ", "faq")]),
        Page("about", "about.html", titled(site, f"About {site.cfg.brand}"),
             f"Who runs {site.cfg.brand}, how the referral model works, who pays us (the facility, never the brand), "
             "and what we will never claim.", nav="about", crumbs=[("About", "about")]),
        Page("contact", "contact.html", titled(site, "Contact and Capacity Check"),
             f"Reach the partnerships lead directly or send the capacity check. We reply within {site.cfg.reply_within}.",
             nav="contact", crumbs=[("Contact", "contact")]),
        Page("privacy", "privacy.html", titled(site, "Privacy"),
             "What the capacity-check form collects, where it goes, and how to have it deleted.", crumbs=[("Privacy", "privacy")]),
        Page("thanks", "thanks.html", titled(site, "Thanks, we have it"), "Your capacity check arrived.",
             noindex=True, in_sitemap=False),
        Page("404", "404.html", titled(site, "Page not found"), "This page is not on the line.", noindex=True, in_sitemap=False),
    ]


def all_pages(site: "SiteContext") -> list[Page]:
    """Every route on the site, home first."""
    return [home_page(site), capabilities_page(site), *category_pages(site), *guide_pages(site), *company_pages(site)]
