# Evidence Layer – current data model (mapping note)

This note documents **what we currently scrape/store** and **where the audit JSON is assembled/stored**, to support adding an Evidence Layer without breaking the pipeline.

## 1) Current scraping output model (DB = source)

Scraping persists raw pages into Postgres table `scraped_pages` (`ScrapedPage`).

### Per-page attributes (today)

Stored in DB (per `ScrapedPage`):
- **url**: canonicalized absolute URL (string)
- **domain**: normalized domain (string)
- **is_target**: target vs competitor (bool)
- **html_content**: raw HTML (string; may be large)
- **text_content**: visible text extracted by BeautifulSoup (string). Current extraction removes: `script`, `style`, `nav`, `footer`, `header`.
- **title**: `<title>` (string)
- **meta_description**: `<meta name="description">` (string)
- **status_code**: HTTP status (int)
- **content_type**: expected `"text/html"` (string)
- **word_count**: `len(text_content.split())` (int)
- **scraped_at**: timestamp
- **url_hash**: SHA256 of normalized URL (string; used for dedup within job in code; DB column is unique)

### What is NOT currently stored (but needed for evidence)

Not explicitly stored/returned today:
- **h1**
- **headings** (h2/h3…)
- **language** (from `<html lang>` or heuristics)
- **links** (menu/internal link graph, CTA anchors)
- **cta** detection
- **pricing** signals/snippets
- **contact** signals/snippets (email/phone/address/contact page)
- **locations** detection
- **structured_data/jsonld** types (`schema.org` Organization/Product/FAQPage…)

These can be deterministically extracted from stored `html_content` (and/or `text_content`) without changing the scraper’s storage schema.

## 2) Typical page volumes (limits)

### Scraping limits
- **Target**: up to **60** pages (`Settings.max_pages_target`)
- **Competitors**: up to **15** pages each (`Settings.max_pages_competitor`)

### Pages actually used for LLM context
LLM stage selects representative pages from DB:
- **Target**: up to **15** pages (`select_representative_pages(max_pages=15)`)
- **Competitors**: up to **10** pages (`select_representative_pages(max_pages=10)`)

Selection favors page types inferred from URL/title: `home`, `about`, `pricing`, `service`, `product`, `case_study`, `faq`, `contact`, `blog`.

### “sampled_urls” in outputs
`appendix.sampled_urls` is currently set to **the first ~10 target pages** selected for context.

## 3) Where JSON is assembled and stored (SSOT)

### Single source of truth (SSOT)
`audit_outputs` table (`AuditOutput`):
- `audit_json`: Stage A (core audit / sales-flow stages)
- `action_plan_json`: Stage B (optional / backward-compatible payload)

### Generation pipeline (high-level)
- Scrape → `scraped_pages`
- LLM stage generates `audit_json` (Stage A)
- Report generator stores outputs into `audit_outputs` and provides URL-first payloads via `/api/audit/{id}/report`


