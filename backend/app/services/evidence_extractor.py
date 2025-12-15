"""
Evidence extraction (deterministic)
==================================

Goal: make scraping visible in the audit output without inventing data.

We DO NOT add random metrics. We only extract quotable evidence from the stored HTML/text:
- headings (H1/H2/H3)
- language (html[lang])
- internal links (nav + body)
- CTA texts
- pricing/contact/location signals (with short snippets)
- structured data types (JSON-LD @type)

This module is intentionally conservative:
- if something is not detected -> return 'not detected' + low confidence evidence (or omit)
- snippets are short and bounded to protect report layout
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup

from app.models import ScrapedPage


_WS_RE = re.compile(r"\s+")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def _norm_ws(s: str) -> str:
    return _WS_RE.sub(" ", (s or "").strip())


def _dedupe_keep_order(items: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for x in items:
        t = _norm_ws(x)
        if not t:
            continue
        k = t.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(t)
    return out


def _truncate(s: str, max_len: int) -> str:
    t = _norm_ws(s)
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def _domain_of(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""


def _is_same_domain(url: str, domain: str) -> bool:
    return _domain_of(url) == (domain or "").lower()


def _extract_jsonld(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for tag in soup.find_all("script", attrs={"type": re.compile(r"application/ld\+json", re.I)}):
        raw = tag.get_text(" ", strip=True)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except Exception:
            continue
        if isinstance(payload, dict):
            out.append(payload)
        elif isinstance(payload, list):
            out.extend([x for x in payload if isinstance(x, dict)])
    return out[:30]  # hard cap


def _jsonld_types(jsonlds: List[Dict[str, Any]]) -> List[str]:
    types: List[str] = []
    for obj in jsonlds:
        t = obj.get("@type")
        if isinstance(t, str):
            types.append(t)
        elif isinstance(t, list):
            types.extend([x for x in t if isinstance(x, str)])
    return _dedupe_keep_order(types)[:20]


def _find_org_name(jsonlds: List[Dict[str, Any]]) -> Optional[str]:
    # Prefer Organization / LocalBusiness name.
    for obj in jsonlds:
        t = obj.get("@type")
        tlist = [t] if isinstance(t, str) else (t if isinstance(t, list) else [])
        tlist2 = [x.lower() for x in tlist if isinstance(x, str)]
        if any(x in {"organization", "localbusiness"} for x in tlist2):
            name = obj.get("name")
            if isinstance(name, str) and _norm_ws(name):
                return _norm_ws(name)
    return None


def _find_locations_from_jsonld(jsonlds: List[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for obj in jsonlds:
        addr = obj.get("address")
        if isinstance(addr, dict):
            parts = []
            for k in ("streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry"):
                v = addr.get(k)
                if isinstance(v, str) and _norm_ws(v):
                    parts.append(_norm_ws(v))
            if parts:
                out.append(", ".join(parts))
        # Some schemas nest location differently; keep conservative.
    return _dedupe_keep_order(out)[:10]


def _best_offer_sentences(text: str) -> Optional[str]:
    """
    Deterministic 1–2 sentence summary from page text.
    Conservative: if we can't find anything that looks like a summary, return None.
    """
    t = _norm_ws(text)
    if not t:
        return None

    # Split into sentence-like chunks.
    chunks = re.split(r"(?<=[.!?])\s+", t)
    chunks = [c.strip() for c in chunks if 40 <= len(c.strip()) <= 260]
    if not chunks:
        return None

    bad = ("cookie", "privacy", "terms", "subscribe", "newsletter", "copyright")
    prefer = ("we ", "our ", "provid", "offer", "help", "build", "deliver", "service", "solution", "product")

    scored: List[Tuple[int, str]] = []
    for c in chunks[:80]:
        lc = c.lower()
        if any(b in lc for b in bad):
            continue
        score = 0
        score += 3 if any(p in lc for p in prefer) else 0
        score += 2 if 80 <= len(c) <= 180 else 0
        scored.append((score, c))

    if not scored:
        return None

    scored.sort(key=lambda x: (-x[0], len(x[1])))
    top = [scored[0][1]]
    # Try second distinct sentence.
    for _, c in scored[1:]:
        if c != top[0] and len(" ".join(top + [c])) <= 360:
            top.append(c)
            break
    return _truncate(" ".join(top), 360)


def _snippets_around(text: str, needles: List[str], *, max_snips: int = 2, window: int = 140) -> List[str]:
    t = text or ""
    if not t:
        return []
    lt = t.lower()
    snips: List[str] = []
    for needle in needles:
        idx = lt.find(needle.lower())
        if idx == -1:
            continue
        start = max(0, idx - window)
        end = min(len(t), idx + len(needle) + window)
        snip = _truncate(t[start:end], 260)
        snips.append(snip)
        if len(snips) >= max_snips:
            break
    return _dedupe_keep_order(snips)


def _extract_headings(soup: BeautifulSoup) -> Tuple[str, List[str]]:
    h1 = ""
    h1_tag = soup.find("h1")
    if h1_tag:
        h1 = _norm_ws(h1_tag.get_text(" ", strip=True))

    heads: List[str] = []
    for tag in soup.find_all(["h2", "h3"]):
        txt = _norm_ws(tag.get_text(" ", strip=True))
        if txt:
            heads.append(txt)
    # Cap to avoid bloating JSON/report.
    return h1, _dedupe_keep_order(heads)[:20]


def _extract_language(soup: BeautifulSoup) -> Optional[str]:
    try:
        html = soup.find("html")
        if html and html.get("lang"):
            return str(html.get("lang")).strip()
    except Exception:
        pass
    return None


def _extract_internal_links(soup: BeautifulSoup, base_url: str, domain: str) -> Tuple[Dict[str, int], List[str]]:
    """
    Returns:
    - counts: url -> count (same-domain only)
    - nav_top: top URLs from nav/header (ordered by frequency)
    """
    counts: Dict[str, int] = {}
    nav_counts: Dict[str, int] = {}

    def add(href: str, is_nav: bool):
        abs_url = urljoin(base_url, href)
        if not _is_same_domain(abs_url, domain):
            return
        # Drop fragments.
        p = urlparse(abs_url)
        abs2 = p._replace(fragment="").geturl()
        counts[abs2] = counts.get(abs2, 0) + 1
        if is_nav:
            nav_counts[abs2] = nav_counts.get(abs2, 0) + 1

    for a in soup.find_all("a", href=True):
        href = a.get("href") or ""
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        # Determine whether it's likely nav.
        is_nav = a.find_parent(["nav", "header"]) is not None
        add(href, is_nav=is_nav)

    nav_top = sorted(nav_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:15]
    return counts, [u for u, _ in nav_top]


def _extract_ctas(soup: BeautifulSoup) -> List[str]:
    """
    Conservative CTA detection: only collect action-ish texts.
    """
    cta_words = (
        "contact",
        "book",
        "schedule",
        "request",
        "get a quote",
        "get quote",
        "quote",
        "demo",
        "call",
        "buy",
        "pricing",
        "plans",
        "start",
        "sign up",
        "signup",
        "trial",
    )
    out: List[str] = []

    def consider(text: str):
        t = _norm_ws(text)
        if not (2 <= len(t) <= 64):
            return
        lt = t.lower()
        if any(w in lt for w in cta_words):
            out.append(t)

    for tag in soup.find_all(["a", "button"]):
        cls = " ".join(tag.get("class") or [])
        txt = tag.get_text(" ", strip=True) if tag else ""
        if not txt:
            continue
        if "btn" in cls.lower() or "button" in cls.lower() or "cta" in cls.lower():
            consider(txt)
        else:
            # Still accept if the text is clearly an action.
            consider(txt)

    return _dedupe_keep_order(out)[:10]


@dataclass(frozen=True)
class EvidenceItem:
    claim: str
    proof_type: str
    source_urls: List[str]
    snippets: List[str]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "proof_type": self.proof_type,
            "source_urls": self.source_urls[:3],
            "snippets": [ _truncate(s, 260) for s in (self.snippets or []) ][:3],
            "confidence": max(0.0, min(1.0, float(self.confidence))),
        }


class EvidenceExtractor:
    def __init__(self, *, max_pages: int = 15):
        self.max_pages = max_pages

    def extract_pages(self, pages: List[ScrapedPage]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for p in (pages or [])[: self.max_pages]:
            out.append(self.extract_page(p))
        return out

    def extract_page(self, page: ScrapedPage) -> Dict[str, Any]:
        html = page.html_content or ""
        soup = BeautifulSoup(html, "lxml") if html else BeautifulSoup("", "lxml")

        lang = _extract_language(soup)
        jsonlds = _extract_jsonld(soup)
        jsonld_types = _jsonld_types(jsonlds)
        h1, headings = _extract_headings(soup)
        ctas = _extract_ctas(soup) if html else []

        internal_counts, nav_top = _extract_internal_links(soup, page.url, page.domain) if html else ({}, [])

        text = page.text_content or ""
        lower = text.lower()

        pricing_needles = ["pricing", "price", "plans", "packages", "starting at", "$", "€", "£", "usd", "eur"]
        pricing_snips = _snippets_around(text, pricing_needles, max_snips=2)
        pricing_detected = bool(pricing_snips) or ("pricing" in lower and len(text) > 200)

        emails = _dedupe_keep_order(_EMAIL_RE.findall(text))[:3]
        phones = _dedupe_keep_order(_PHONE_RE.findall(text))[:3]
        contact_needles = ["contact", "call", "email", "phone", "address"]
        contact_snips = _snippets_around(text, contact_needles, max_snips=2)
        contact_detected = bool(emails or phones or contact_snips or ("contact" in (page.url or "").lower()))

        locations = _find_locations_from_jsonld(jsonlds)
        # fallback: address-ish snippet from text
        if not locations:
            addr_snips = _snippets_around(text, ["address", "located", "location"], max_snips=1)
            if addr_snips:
                locations = addr_snips

        return {
            "url": page.url,
            "title": page.title or "",
            "meta_description": page.meta_description or "",
            # Keep a short excerpt for offer/company extraction (bounded for layout safety).
            "text_excerpt": _truncate(page.text_content or "", 1200),
            "language": lang or "not detected",
            "h1": h1 or "not detected",
            "headings": headings,
            "cta_detected": ctas,
            "structured_data_types": jsonld_types,
            # Provide a small slice of JSON-LD for deterministic entity extraction (not for LLM quoting).
            "jsonld": jsonlds[:6],
            "internal_links_top": nav_top[:10],
            "signals": {
                "pricing_detected": pricing_detected,
                "pricing_snippets": pricing_snips,
                "contact_detected": contact_detected,
                "contact_snippets": contact_snips,
                "emails_detected": emails,
                "phones_detected": phones,
                "locations_detected": locations[:5],
            },
            # Keep counts out of JSON by default to avoid turning this into a metric layer.
            "debug": {
                "internal_links_unique": len(internal_counts),
            },
        }

    def build_company_profile(self, pages: List[Dict[str, Any]], *, fallback_domain: str) -> Dict[str, Any]:
        # Company name: from JSON-LD on any page (prefer home first if present).
        company_name: Optional[str] = None
        primary_language = None
        services: List[str] = []
        locations: List[str] = []
        offer_summary = None

        # language: pick first non-not-detected
        for p in pages:
            lang = (p.get("language") or "").strip()
            if lang and lang.lower() != "not detected":
                primary_language = lang
                break

        # services: pull from H1/headings on home/service-ish pages first.
        for p in pages:
            url = (p.get("url") or "").lower()
            title = (p.get("title") or "").lower()
            is_home = urlparse(url).path.rstrip("/") in {"", "/"}
            is_services = ("service" in url) or ("services" in url) or ("services" in title)
            if not (is_home or is_services):
                continue
            h1 = p.get("h1") or ""
            hs = p.get("headings") or []
            cand = []
            if isinstance(h1, str) and h1.lower() != "not detected":
                cand.append(h1)
            if isinstance(hs, list):
                cand.extend([x for x in hs if isinstance(x, str)])
            # Filter generic headings
            generic = {"home", "welcome", "about", "services", "products", "solutions", "contact"}
            cand2 = []
            for c in cand:
                t = _norm_ws(c)
                if 3 <= len(t) <= 80 and t.lower() not in generic:
                    cand2.append(t)
            services.extend(cand2)

        services = _dedupe_keep_order(services)[:12]

        # company name from JSON-LD (prefer home first)
        def iter_pages_prefer_home() -> Iterable[Dict[str, Any]]:
            homes = []
            others = []
            for p in pages:
                url = (p.get("url") or "").lower()
                if urlparse(url).path.rstrip("/") in {"", "/"}:
                    homes.append(p)
                else:
                    others.append(p)
            return list(homes) + list(others)

        for p in iter_pages_prefer_home():
            jsonld = p.get("jsonld")
            if isinstance(jsonld, list):
                name = _find_org_name([x for x in jsonld if isinstance(x, dict)])
                if name:
                    company_name = name
                    break

        # locations
        for p in pages:
            sig = p.get("signals") or {}
            locs = sig.get("locations_detected") if isinstance(sig, dict) else []
            if isinstance(locs, list):
                locations.extend([x for x in locs if isinstance(x, str)])
        locations = _dedupe_keep_order(locations)[:10]

        # offer summary: deterministic 1–2 sentences from homepage text_excerpt; fallback meta_description.
        for p in pages:
            url = (p.get("url") or "").lower()
            is_home = urlparse(url).path.rstrip("/") in {"", "/"}
            if not is_home:
                continue
            tx = p.get("text_excerpt") or ""
            if isinstance(tx, str):
                offer_summary = _best_offer_sentences(tx)
            if offer_summary:
                break
        if not offer_summary:
            # fallback: homepage meta description, else first non-trivial meta description
            for p in iter_pages_prefer_home():
                md = p.get("meta_description") or ""
                if isinstance(md, str) and len(_norm_ws(md)) >= 60:
                    offer_summary = _truncate(md, 260)
                    break

        # company_name fallback: domain
        if not company_name:
            company_name = fallback_domain or "this domain"

        return {
            "company_name": company_name,
            "primary_offer_summary": offer_summary or "not detected",
            "services_detected": services,
            "locations_detected": locations,
            "primary_language_detected": primary_language or "not detected",
            "top_pages": self._top_pages(pages),
        }

    def _top_pages(self, pages: List[Dict[str, Any]]) -> List[str]:
        counts: Dict[str, int] = {}
        for p in pages:
            for u in (p.get("internal_links_top") or []):
                if isinstance(u, str) and u:
                    counts[u] = counts.get(u, 0) + 1
        top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
        return [u for u, _ in top]

    def build_evidence_items(
        self,
        *,
        pages: List[Dict[str, Any]],
        company_profile: Dict[str, Any],
        locale: Optional[str],
    ) -> List[EvidenceItem]:
        """
        Deterministic evidence set used by LLM + UI citations.
        Keep it small and high-signal.
        """
        ev: List[EvidenceItem] = []

        urls = [p.get("url") for p in pages if isinstance(p.get("url"), str)]

        def add(claim: str, proof_type: str, source_urls: List[str], snippets: List[str], confidence: float):
            ev.append(
                EvidenceItem(
                    claim=_truncate(claim, 240),
                    proof_type=proof_type,
                    source_urls=_dedupe_keep_order(source_urls)[:3],
                    snippets=_dedupe_keep_order(snippets)[:3],
                    confidence=confidence,
                )
            )

        # Pricing / Contact / About pages by URL heuristics.
        pricing_urls = [u for u in urls if isinstance(u, str) and any(k in u.lower() for k in ["pricing", "prices", "price", "plans"])]
        contact_urls = [u for u in urls if isinstance(u, str) and "contact" in u.lower()]
        about_urls = [u for u in urls if isinstance(u, str) and "about" in u.lower()]

        # Pricing signal evidence
        pricing_snips = []
        for p in pages:
            sig = p.get("signals") or {}
            if isinstance(sig, dict) and sig.get("pricing_snippets"):
                pricing_snips.extend([x for x in sig.get("pricing_snippets") if isinstance(x, str)])
        if pricing_urls or pricing_snips:
            add(
                claim="Pricing information is detectable, but may not be structured for AI quoting.",
                proof_type="pricing_present",
                source_urls=pricing_urls[:3] if pricing_urls else urls[:1],
                snippets=pricing_snips[:2],
                confidence=0.75 if pricing_urls else 0.55,
            )
        else:
            add(
                claim="No pricing page or pricing section was detected in the sampled pages.",
                proof_type="no_pricing",
                source_urls=company_profile.get("top_pages")[:3] if isinstance(company_profile.get("top_pages"), list) else urls[:1],
                snippets=["not detected"],
                confidence=0.65,
            )

        # Contact evidence
        contact_snips = []
        emails = []
        phones = []
        for p in pages:
            sig = p.get("signals") or {}
            if isinstance(sig, dict):
                contact_snips.extend([x for x in (sig.get("contact_snippets") or []) if isinstance(x, str)])
                emails.extend([x for x in (sig.get("emails_detected") or []) if isinstance(x, str)])
                phones.extend([x for x in (sig.get("phones_detected") or []) if isinstance(x, str)])
        if contact_urls or emails or phones or contact_snips:
            add(
                claim="Contact details exist, but must be presented in a consistent, AI-quotable block.",
                proof_type="contact_present",
                source_urls=(contact_urls[:2] or urls[:2]),
                snippets=_dedupe_keep_order((emails + phones + contact_snips))[:2],
                confidence=0.8 if contact_urls else 0.6,
            )
        else:
            add(
                claim="No clear contact page, email, or phone was detected in the sampled pages.",
                proof_type="no_contact",
                source_urls=company_profile.get("top_pages")[:3] if isinstance(company_profile.get("top_pages"), list) else urls[:1],
                snippets=["not detected"],
                confidence=0.65,
            )

        # Entity/Organization signals
        sd_types = []
        for p in pages:
            for t in (p.get("structured_data_types") or []):
                if isinstance(t, str):
                    sd_types.append(t)
        sd_types = _dedupe_keep_order(sd_types)
        if any(t.lower() in {"organization", "localbusiness"} for t in sd_types):
            add(
                claim="Entity signals are present in structured data (Organization/LocalBusiness).",
                proof_type="entity_signals_present",
                source_urls=urls[:2],
                snippets=[f"structured_data_types: {', '.join(sd_types[:6])}"],
                confidence=0.8,
            )
        else:
            add(
                claim="No Organization/LocalBusiness structured data was detected in sampled pages.",
                proof_type="weak_entity_signals",
                source_urls=urls[:2],
                snippets=[f"structured_data_types: {', '.join(sd_types[:6]) if sd_types else 'not detected'}"],
                confidence=0.6,
            )

        # Language mismatch (locale vs detected)
        if locale and isinstance(locale, str) and locale.strip():
            detected = (company_profile.get("primary_language_detected") or "").lower()
            loc = locale.lower()
            # Rough check: cs-CZ -> cs, en-US -> en
            loc2 = loc.split("-")[0]
            det2 = detected.split("-")[0] if detected and detected != "not detected" else ""
            if det2 and loc2 and det2 != loc2:
                add(
                    claim=f"Primary language on the site appears to differ from the requested locale ({locale}).",
                    proof_type="language_mismatch",
                    source_urls=urls[:2],
                    snippets=[f"html_lang_detected: {company_profile.get('primary_language_detected')}"],
                    confidence=0.7,
                )

        # Fragmented services: if we have multiple services_detected but no clear service pages.
        services = company_profile.get("services_detected") if isinstance(company_profile.get("services_detected"), list) else []
        has_service_url = any(isinstance(u, str) and "service" in u.lower() for u in urls)
        if services and not has_service_url:
            add(
                claim="Service information appears present, but not organized into dedicated service explanation pages.",
                proof_type="fragmented_content",
                source_urls=urls[:3],
                snippets=[f"services_detected: {', '.join([s for s in services[:5] if isinstance(s, str)])}"],
                confidence=0.6,
            )

        # Cap total evidence items (layout safety)
        return ev[:12]

    def build_evidence_layer(
        self,
        *,
        pages: List[ScrapedPage],
        fallback_domain: str,
        locale: Optional[str],
    ) -> Dict[str, Any]:
        page_blocks = self.extract_pages(pages)
        company_profile = self.build_company_profile(page_blocks, fallback_domain=fallback_domain)
        evidence_items = self.build_evidence_items(pages=page_blocks, company_profile=company_profile, locale=locale)
        return {
            "company_profile": company_profile,
            "pages": page_blocks,
            "evidence": [e.to_dict() for e in evidence_items],
        }


