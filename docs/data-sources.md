# Data Source Register

> **Source of truth for all external data dependencies.** Every source used in the system must be listed here with its license, access method, rate limits, and retrieval log.

---

## Sources from PLAN.md Appendix D

| # | Source | Used In | Access | License / Terms | Status | Notes |
|---|--------|---------|--------|-----------------|--------|-------|
| 1 | Synthetic generator (in-house) | Phase 2+ | Local | Project license (MIT) | ✅ Planned | Always tagged `is_synthetic=true` |
| 2 | Manufacturer spec sheets | Phase 1 | Manual entry | Public facts | ✅ Planned | Curated seed, not scraped |
| 3 | Wikidata | Phase 1 (optional) | SPARQL endpoint | CC0 | 🔲 Optional | Canonical IDs for SKUs |
| 4 | eBay Browse API | Phase 3 | Free developer key | eBay API Terms | 🔲 Planned | Active listings only, attribution required |
| 5 | eBay Marketplace Insights (sold) | Phase 3 (optional) | Restricted, apply | eBay API Terms | 🔲 Optional | May be denied, do not depend on it |
| 6 | Partner CSV imports | Phase 3, 5 | Upload / SFTP | Partner agreement | 🔲 Planned | Highest-priority price signal |
| 7 | FRED API | Phase 3 | Free API key | Public data, FRED Terms | 🔲 Planned | Monthly, lagged, verify series IDs |
| 8 | Wikimedia Pageviews API | Phase 3 | No key, User-Agent required | CC0 data, Wikimedia policies | 🔲 Planned | Demand proxy, cache aggressively |
| 9 | Google Trends (pytrends) | Optional | Unofficial library | Google Terms, fragile | 🔲 Optional | Cache aggressively or skip |
| 10 | iFixit API | Phase 2+ (optional) | Free API | Content may be CC BY-NC-SA | 🔲 Optional | Commercial use restricted, use facts only |
| 11 | Kaggle / UCI datasets | Phase 2 prototyping | Download | Check each license | 🔲 Optional | Not for production without license check |
| 12 | NIST SP 800-88 Rev. 1 | Phase 2, 5 | Public document | US Government Work | ✅ Reference | Basis for wipe certificates |
| 13 | PHMSA, DOT battery rules | Phase 2 | Public regulation | Public | ✅ Reference | Information only |
| 14 | R2, e-Stewards directories | Phase 2 | Public lists | Public | 🔲 Reference | Verify current status |
| 15 | IRS Pub 526, 561 | Phase 2 | Public | Public | ✅ Reference | Information only, not tax advice |

---

## Excluded Sources (Do Not Use)

| Source | Reason |
|--------|--------|
| Keepa | Paid, ToS prohibits scraping |
| DRAMeXchange | Paid subscription required |
| Jungle Scout | Paid, ToS prohibits scraping |
| Sites whose ToS prohibit scraping | Legal risk |
| Apple / retailer data without authorization | No authorization |
| Paid LLM APIs (OpenAI, Anthropic, etc.) | Hard dependency on paid service forbidden |

---

## Retrieval Log

*Automatically updated by ingestion pipelines. Manual entries for reference sources.*

| Source | Last Retrieved | Rows | Status | Error Count | Next Scheduled |
|--------|----------------|------|--------|-------------|----------------|
| — | — | — | — | — | — |

---

## Adding a New Source

1. Verify license is compatible (MIT, Apache-2.0, BSD, CC0, Public Domain, or explicit free tier)
2. Confirm access method (official API, public dataset, partner agreement)
3. Document rate limits and pagination
4. Add row to table above with status `🔲 Planned`
5. Create ADR documenting the decision
6. Implement adapter with `source` and `as_of` on every record
7. Add health check endpoint (`/api/v1/sources/health`)
8. Update retrieval log after first successful run

---

## License Compliance Checklist

- [ ] Every source has a verified license in this register
- [ ] No AGPL-3.0 or copyleft libraries used as runtime dependencies (Grafana, Loki are infra only)
- [ ] All scraped data respects `robots.txt` and ToS
- [ ] Partner data covered by written agreement
- [ ] Attribution displayed in UI where required (e.g., eBay)
- [ ] `source` and `as_of` fields on every price/observation record

---

*Last updated: 2026-10-20*
*Version: 1.0*