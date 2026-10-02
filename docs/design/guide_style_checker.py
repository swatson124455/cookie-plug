# ARCHIVED session helper (2026-09-29), kept so its house-style rules for guides are not lost.
# Out of date: SLUGS and CATEGORIES are hardcoded (13 guides and 8 line pages exist now) and it
# requires a sources key that one guide lacks. Not run by tests or CI. See docs/HANDOFF.md.

"""Validate the Markdown guides: front matter, lengths, links, punctuation."""
import re
import sys
from pathlib import Path

import yaml

GUIDES = Path("/home/user/cookie-plug/site/content/guides")
SLUGS = {
    "how-to-find-a-cookie-co-packer", "co-packer-minimums-lead-times-and-costs",
    "when-to-leave-the-commissary", "how-to-find-a-dog-treat-co-packer",
    "refrigerated-to-shelf-stable", "what-retailers-require-from-a-new-supplier",
    "second-source-co-packer-strategy", "from-farmers-market-to-packaged-product",
}
CATEGORIES = {"cookie-co-packer", "bakery-co-packer", "dog-treat-co-packer", "pet-food-co-packer", "general"}
KEYS = ["title", "seo_title", "description", "date", "updated", "category", "summary", "related", "sources"]


def split(text):
    lines = text.split("\n")
    assert lines[0] == "---", "file must start with ---"
    end = lines.index("---", 1)
    return "\n".join(lines[1:end]), "\n".join(lines[end + 1:])


def rendered_words(body):
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)       # links -> anchor text
    text = re.sub(r"^\|?[\s|:-]+\|?$", " ", text, flags=re.M)   # table separator rows
    text = text.replace("|", " ")
    text = re.sub(r"[#*`>]", " ", text)
    return [w for w in text.split() if re.search(r"[A-Za-z0-9]", w)]


def check(path):
    problems = []
    text = path.read_text(encoding="utf-8")
    fm_text, body = split(text)
    fm = yaml.safe_load(fm_text)
    for k in KEYS:
        if k not in fm:
            problems.append(f"missing key {k}")
    title, seo, desc, summ = fm["title"], fm["seo_title"], fm["description"], fm["summary"]
    if len(title) > 75: problems.append(f"title {len(title)} chars")
    if len(seo) > 60: problems.append(f"seo_title {len(seo)} chars")
    if not 120 <= len(desc) <= 155: problems.append(f"description {len(desc)} chars")
    sw = len(summ.split())
    sentences = len(re.findall(r"[.?]( |$)", summ))
    if not 45 <= sw <= 80: problems.append(f"summary {sw} words")
    if not 2 <= sentences <= 3: problems.append(f"summary {sentences} sentences")
    if fm["category"] not in CATEGORIES: problems.append("bad category")
    rel = fm["related"]
    if not (2 <= len(rel) <= 3 and all(r in SLUGS and r != path.stem for r in rel)):
        problems.append(f"bad related {rel}")
    urls = [s["url"] for s in fm["sources"]]
    for s in fm["sources"]:
        if set(s) != {"title", "url"}: problems.append(f"bad source {s}")
    if not body.lstrip().startswith("## "): problems.append("body does not start with H2")
    if re.search(r"^# ", body, flags=re.M): problems.append("H1 in body")
    if "—" in text or "–" in text: problems.append("em or en dash present")
    if "!" in re.sub(r"\([^)]*\)", "", body): problems.append("exclamation mark")
    if re.search(r"open line", text, flags=re.I): problems.append("mentions Open Line")
    links = re.findall(r"\]\(([^)]+)\)", body)
    used = set()
    for link in links:
        if link.startswith("/guides/"):
            slug = link.strip("/").split("/")[-1]
            if slug not in SLUGS or not link.endswith("/"): problems.append(f"bad guide link {link}")
        elif link in urls:
            used.add(link)
        else:
            problems.append(f"link not in sources: {link}")
    unused = [u for u in urls if u not in used]
    tables = len(re.findall(r"^\|[\s:|-]+\|$", body, flags=re.M))
    if tables > 1: problems.append(f"{tables} tables")
    words = rendered_words(body)
    raw = len(body.split())
    if not 900 <= len(words) <= 1400: problems.append(f"body {len(words)} words")
    print(f"== {path.name}")
    print(f"   title {len(title)} | seo {len(seo)} | desc {len(desc)} | summary {sw}w/{sentences}s | body {len(words)} words (raw tokens {raw}) | sources {len(urls)} | tables {tables}")
    for u in unused:
        print(f"   note: source not linked in body: {u}")
    for p in problems:
        print(f"   PROBLEM: {p}")
    return not problems


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(p.name for p in GUIDES.glob("*.md"))
    ok = all([check(GUIDES / n) for n in names])
    sys.exit(0 if ok else 1)
