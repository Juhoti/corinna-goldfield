# Corinna / Pieman Goldfield — Historical Source-Pack

Cross-reference partner to `corinna_workflow.py`. The script shows you **where
the Tertiary lead gravel sits** (mappable). These documents tell you **what the
old-timers found and — crucially — which way the field spread upstream** (rich
detail, fuzzy location). You marry the two by matching described localities to
mapped drainages in QGIS.

All links below were checked and resolve as of assembly. If one 404s later,
search the title at the Tasmanian Parliament digitised papers
(parliament.tas.gov.au) or the Journal of Australasian Mining History
(mininghistory.asn.au).

---

## TIER A — primary sources (the old-timers themselves)

### 1. Thureau 1881 — *Report on West Coast Mines No.1: Pieman River Goldfield*
Parliamentary Paper 82/1881. The single most important document for your
question. Inspector of Mines, writing at the moment of the rush.
- **Why it matters:** Thureau explicitly urged miners "who had hitherto only
  worked the creeks to tunnel into the **'tertiary washes'**" — i.e. he
  identified the deep lead as the real prize in 1881. Your whole upstream/lead
  thesis is his thesis.
- **What to mine:** his "impressionistic map" of the field (reproduced as Fig.1
  in Haygarth below), and his descriptions of which ground was "terraces"
  (elevated Tertiary) vs worked creek. Elevated terrace = lead remnant = your
  target.
- **Find it:** Tasmanian Parliament digitised papers, 1881, Paper 82. (Haygarth
  reproduces the key map and quotes.)

### 2. Thureau 1884 — *Mount Cleveland and Corinna Gold Fields*
Parliamentary Paper 104/1884.
- Thureau returns; still convinced "coarse gold indicated a much larger goldfield
  than yet uncovered," blaming dense scrub and **auriferous drifts buried under
  more recent gravels and hard conglomerates** for hiding it. That "buried under
  younger gravel" is a direct description of deep-lead cover — and his belief that
  the field was under-explored is period support for looking further/upslope.

### 3. Montgomery 1894 — *Report on the Corinna Goldfield*
Secretary of Mines Report 1893–94, pp. xxix–xxxix.
- The most systematic 1890s account. Montgomery noted the gold was "flattened,
  rounded and concentrated in sandy carbonaceous 'bottoms'" (palaeosols) — i.e.
  the gutter of the old lead. Good for understanding what the pay looks like.

### 4. Smith 1897 — *Report on the mineral district between Corinna and Waratah*
Secretary of Mines Report 1896–97, pp. xliii–liii.
- Source of the **600–900 kg estimate for Main Rivulet and tributaries** (the
  field's richest number). Read for which upper tributaries he rated.

### 5. Blake 1939 — *Report on Corinna alluvial goldfield*
Unpubl. Report Dep. Mines Tasm. 1939:26–46. (Also Henderson 1939, same vol.)
- The last systematic field report before the modern era. Establishes the
  "Browns Plains Gravels" as the Tertiary lead unit. Held at MRT; request via
  info@mrt.tas.gov.au or the MRT library.

---

## TIER B — modern history (does the archival legwork for you)

### 6. Haygarth 2012 — *An 'Island' Within an Island: ... Pieman River Goldfield
1877–85* — Journal of Australasian Mining History, vol.10, pp.55–71.
**FREE PDF, verified:**
https://www.mininghistory.asn.au/wp-content/uploads/5.-Haygarth.COMPLETED5.Vol-10.compressed.pdf
- The best single read. Reproduces Thureau's 1881 map. Narrates **the exact
  sequence the field spread upstream** — this is your upstream roadmap:
  - Browns Plains (Jack Brown & Ah Chow, Dec 1878) — first strike, north side.
  - Middletons Creek (Middleton & Tengdahl, 1879) — Savage R tributary, 250 diggers.
  - **Sunday (now Sabbath) Creek** — Donaldson R tributary — "next to be rushed."
  - **"The Badger" (now Longback Creek)** — under the Longback hill.
  - **Hangmans Creek** — 30 men "15 km upstream from the Pieman stores."
  - **Frenchmans Creek** — St Dizier "chased gold **HIGH ABOVE** the middle reaches."
  - Nancy / Lucy / Amelia / Alice Creeks — named by the Slaters.
  - **Lucy Spur mine — at the HEAD of Lucy Creek** (Spurr's reef claim).
  - Long Plains rush (Feb 1882) — Peevor & Johnson, 4000+ oz coarse gold.
  - Rocky River (McGinty 1883) — the 243 & 144 oz nuggets.
  - Specimen Reef / Golden Ridge — the reef sources feeding the alluvials.
- **Osmiridium note:** the Pieman was a *better osmiridium field than gold*
  (14,000+ oz Os-Ir vs ~31,500 oz Au), concentrated on Savage R tributaries. If
  your detector/pan turns up heavy silver-grey grains that aren't gold, that's
  osmiridium — historically worth more per oz than the gold.

### 7. Haygarth (hydraulic craze paper) — *The disastrous hydraulic gold craze in
Tasmania 1893–1901* — mininghistory.asn.au. **Verified PDF:**
https://www.mininghistory.asn.au/wp-content/uploads/3.-Haygarth2V20b.pdf
- Covers the 1890s attempt to hydraulic-sluice the elevated Tertiary terraces —
  i.e. exactly the lead remnants. Tells you which high terraces they targeted
  (and why it failed: terraces too elevated for the water pressure, wash too
  thin). Their target terraces = your lead-remnant map.

### 8. Back-Tracks Heritage Consultants 1997 — *Lucy Spur Goldfield: Historic
Heritage Assessment* — Archaeological Survey Report 97/01, MRT.
- Site-specific archaeology of the Lucy Spur workings (head of Lucy Creek). If
  Lucy Ck comes up clear on the workflow, this tells you exactly what's there.
  Request via MRT.

---

## TIER C — newspapers (the week-by-week record)

The Tasmanian papers covered the Pieman rushes in real time: which creek was
rushed when, claim disputes, escort figures, store locations. The Mercury
(Hobart), Launceston Examiner, and later the Zeehan & Dundas Herald are all
digitised on Trove. Run `python3 trove_links.py` for ready-made searches per
target creek (no account needed), or get a free API key and run
`TROVE_API_KEY=xxx python3 trove_links.py --api` for article counts and first
hits sorted oldest-first — the 1879-1885 hits are the rush itself.

What to mine from them: distances and directions in prose ("15 km upstream
from the Pieman stores"), which stores/landings creeks were measured from,
and names that never made the official reports. Cross-reference against
`locate_creeks.py` — if a newspaper names a creek, the name may survive in
the LIST hydrography layer.

## TIER D — archives, registers and field media

### Placenames Tasmania / LIST "Named Features" layer
`Public/SearchService/MapServer/0` on the LIST ArcGIS REST endpoint. The
registered nomenclature for the field, including superseded and unofficial
names: SUNDAY CREEK (Sabbath Creek's 1879 name and its current hydrography
name), SYDNEY TOM CREEK (Hangmans Creek's alias), CHINAMAN CREEK
(superseded), McGINTY CREEK, LINGER AND DIE CREEK, TUNNELRACE CREEK. This is
the bridge between names in the 1880s reports and the modern map: check it
before concluding a creek name is lost. Integrated as `placenames.py` (with
`creek_aliases.json` for outright renames); `reach_analysis.py` and
`locate_creeks.py` resolve historical names through it automatically.

### Libraries Tasmania / Tasmanian Archives
librariestas.ent.sirsidynix.net.au (catalogue) and stors.tas.gov.au
(digitised items). Photographs, mining charts, correspondence and diaries
for the west coast fields. Browser access only.

### UTAS ePrints — eprints.utas.edu.au
University of Tasmania open repository: geology theses and history papers
covering the Corinna–Pieman area. Machine-readable search:
`/cgi/search/simple?q=Pieman+gold&output=Atom`.

### Royal Society of Tasmania — rst.org.au
Papers and Proceedings from the 1850s onward; early geological accounts of
the west coast pre-date the Mines Department record.

### Field documentation on YouTube
Rob Parsons (youtube.com/c/RobParsons1) documents relocated and previously
unrecorded workings across western Tasmania, including the Corinna–Waratah
country. Video descriptions and footage occasionally identify localities
that appear in no published dataset. Treat as leads for cross-referencing
against the occurrence and nomenclature layers, not as verified positions.

## HOW TO CROSS-REFERENCE (the actual method)

1. Run `corinna_workflow.py` → get each target's lead + tenure status, and the
   `corinna_result.geojson`.
2. Open that GeoJSON in QGIS over MRT 1:25k geology + a topo basemap.
3. From Haygarth (#6), take the **upstream named creeks** — Sabbath, Longback,
   Hangmans, upper Frenchmans, head of Lucy — and find them on the map.
4. Look for where those upstream creeks **cross mapped Tertiary gravel**
   (Browns Plains Gravels). That intersection, if it's clear of tenement AND
   outside the Savage River Regional Reserve, is your prime unworked lead-fed
   ground.
5. Confirm tenure on LISTmap for every candidate before travelling.

## THE HONEST CAVEATS
- "Not in the modern appendix" ≠ "unworked & rich." The old-timers walked every
  drainage; some upstream ground is un-named because it was tried and pinched
  out, not missed. History tells you where they *went*, not where gold *remains*.
- Several named creeks (Longback, Hangmans) have **no grid ref** — they're
  archival-only. Locating them is your own map-and-ground work.
- Most of the genuinely remote upper country trends toward the **Savage River
  Regional Reserve / Tarkine**, where prospecting is prohibited. Remote and
  unworked often means protected. The reserve check is non-negotiable.
- Coordinates in the target file are ~100–200 m. Right creek, not right rock.
