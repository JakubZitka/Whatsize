# WhatSize — Deployment plán

**Verze:** 1.0 · **Datum:** 28. 8. 2026 · **Vychází z:** WhatSize PRD v1.0
**Rozhodnuto se stakeholderem:** mobilní app ve Flutteru · backend na Hetzner Cloud (EU) · bez dedikovaného ops člověka (infrastrukturu obsluhují vývojáři) · backend stack dle návrhu níže

---

## 1. Shrnutí

MVP WhatSize (CZ/SK/PL, cíl §11 PRD: 1 M profilů, 10 M doporučení/měs jako design point) lze provozovat za **~130–170 € měsíčně** na Hetzner Cloud, s růstem na **~600–900 €/měs** při plném design pointu. Největší náklady deploymentu nejsou infrastruktura, ale jednorázové položky: penetrační test (NFR, ~5–15 k€/rok), účty ve storech a čas na počáteční setup (~10–14 dev-dní).

Architektura je záměrně jednoduchá — dva aplikační servery za load balancerem, jeden databázový server, vše v Dockeru, deploy přes GitHub Actions. Žádný Kubernetes: tým bez dedikovaného ops nemá platit daň za orchestrátor, který MVP nepotřebuje.

## 2. Stack

| Vrstva | Volba | Zdůvodnění |
|---|---|---|
| Mobilní app | **Flutter** (iOS 16+, Android 10+) | Rozhodnuto. Jedna codebase, vlastní vykreslování sedí na siluetu (FR-1.4) a plně custom UI. |
| Backend API | **Python 3.12 + FastAPI** | Matching engine, kalibrace offsetů a reverse-measurement estimátor jsou statisticko-datové úlohy — Python je pro ně nejsilnější ekosystém (NumPy/SciPy/pandas) a tentýž jazyk poslouží ingestion pipeline. FastAPI dává async výkon a OpenAPI schéma zdarma (z něj se generuje Dart klient). |
| Databáze | **PostgreSQL 16** | Relační model přesně kopíruje workbook (dim/fact/ref tabulky). Postgres zvládne i logování doporučení (observability NFR) do partitionované tabulky; na ClickHouse je čas až ve Phase 2–3. |
| Cache | **Redis 7** | Size charty pro 100–500 brandů jsou malé (13,7 k → 50 k řádků) — celé se vejdou do paměti. Warm-cache lookup < 300 ms p95 je pak triviální. |
| Object storage | **Hetzner Object Storage (S3 kompatibilní)** | Zálohy DB (WAL archiv), exporty, bundly size chartů pro offline cache v appce. |
| CDN / TLS edge | **Cloudflare (free)** | CDN pro chart bundly a statiku, DDoS ochrana, DNS. |
| Kontejnerizace | **Docker + Docker Compose** | Jednoduché, reprodukovatelné, bez orchestrátoru. |

## 3. Prostředí

| Prostředí | Účel | Infrastruktura |
|---|---|---|
| **dev** | lokální vývoj | `docker compose up` na stroji vývojáře (API + Postgres + Redis) |
| **staging** | validace před releasem, review buildů z TestFlight/Play internal | 1× malý VPS (CPX21), celý stack v jednom compose |
| **prod** | ostrý provoz | viz §4 |

Staging běží na anonymizovaných/syntetických datech — nikdy na kopii ostrých tělesných měr (GDPR §10 PRD).

## 4. Produkční architektura (Hetzner)

```
                    Cloudflare (DNS, CDN, WAF)
                            │
                  Hetzner Load Balancer (LB11)
                     │                │
              app-1 (CPX31)     app-2 (CPX31)
              FastAPI + Redis   FastAPI + Redis
                     │                │
                     └───────┬────────┘
                             │  privátní síť (Hetzner vSwitch)
                      db-1 (CPX41)
                      PostgreSQL 16
                      šifrovaný volume 100 GB
                             │
              Hetzner Object Storage (zálohy, bundly)
```

- **Region:** Falkenstein (FSN1); zálohy replikované do Norimberku — obojí EU, splňuje požadavek na uložení dat v EU.
- **Dva app servery** za LB: rolling deploy bez výpadku, odolnost proti výpadku jednoho stroje. Redis běží na obou app serverech jako lokální cache (charty jsou read-mostly a malé; invalidace přes pub/sub kanál v Postgres LISTEN/NOTIFY — bez samostatného Redis clusteru).
- **Postgres na vlastním VM**, ne v compose s aplikací. Hetzner nemá managed Postgres, proto:
  - šifrovaný volume (LUKS) — encryption at rest;
  - sloupce s tělesnými mírami navíc šifrované aplikačně (pgcrypto/aplikační vrstva) — měření nečitelná i z DB dumpu;
  - **pgBackRest**: denní full backup + průběžný WAL archiv do Object Storage → RPO ≈ 5 min, RTO ≈ 1–2 h; obnova testovaná měsíčně (automatizovaný restore-test job do dočasného VM).
- **Privátní síť**: DB není dostupná z internetu; SSH jen přes klíče, fail2ban, automatické bezpečnostní aktualizace (unattended-upgrades).
- **Cron/worker kontejner** na app-1: ingestion pipeline (Tier 1 scraping P1 brandů, change detection), kalibrační job offsetů (FR-5.3), validace chart dat (kvaranténa dle NFR).

### Škálování k design pointu (1 M profilů, 10 M doporučení/měs)

10 M doporučení/měs ≈ 4 req/s průměr, ~40 req/s špička — to zvládnou 2× CPX31 s rezervou; škálování je „přidej třetí app server do LB" (10 minut práce). DB upgrade CPX41 → CCX (dedikované vCPU) + read replika až podle reálné zátěže. Žádný architektonický zlom před Phase 3.

## 5. CI/CD

### Backend (GitHub Actions)
1. PR → lint, testy, **8 golden test fixtures** z workbooku (§8.9 PRD) jako povinný gate.
2. Merge do `main` → build Docker image → GitHub Container Registry.
3. Deploy job: SSH na app servery, `docker compose pull && up -d` postupně (app-1, health check přes LB, app-2). Rollback = redeploy předchozího tagu image.
4. DB migrace přes Alembic, spouštěné před rolloutem, vždy zpětně kompatibilní o jednu verzi (expand–contract), aby rolling deploy nikdy neběžel proti nekompatibilnímu schématu.

### Mobilní app (Codemagic + fastlane)
- **Codemagic** (CI stavěné pro Flutter, macOS buildy v ceně; free tier 500 min/měs stačí na start).
- fastlane: podpis, upload do **TestFlight** a **Play Internal testing** z každého merge do `main`.
- Release kanály: internal → closed beta (CZ/SK/PL testeři) → production se **staged rolloutem** (Play 10 → 50 → 100 %, App Store phased release).
- Store metadata ve 4 jazycích (CZ, SK, PL, EN) verzovaná v repu (fastlane deliver/supply).
- **Offline požadavek (NFR):** app si stahuje bundle size chartů oblíbených brandů přes CDN (verzovaný JSON/SQLite balíček z Object Storage) — velikost dat i při 500 brandech v jednotkách MB.

### Verzování dat
Size charty jsou produkt (kritická cesta P0). Ingestion výstupy procházejí stejným PR flow jako kód: automatické validace (monotonie, kontiguita, measurement_basis) → kvaranténa při selhání → publikace nové verze bundlu.

## 6. Observabilita a provoz bez ops člověka

| Oblast | Nástroj | Cena |
|---|---|---|
| Chyby app i backendu | **Sentry** (EU data residency) | Team ~26 $/měs |
| Uptime + alerty | **Better Stack / UptimeRobot** | free tier |
| Metriky + logy | **Grafana Cloud free tier** (Prometheus agent + Loki) | 0 € |
| Produktová analytika | **PostHog Cloud EU** | free do 1 M eventů/měs |
| Log doporučení (NFR: rekonstruovatelnost každé odpovědi) | partitionovaná tabulka v Postgres (vstupy, kandidáti, vítěz, confidence) | v ceně DB |

Tvrdé pravidlo z PRD: **žádná tělesná míra nesmí do analytických eventů, logů ani crash reportů** — vynuceno scrubbing middlewarem na backendu a lint pravidlem pro analytické eventy v appce (allowlist polí, ne blocklist).

Interní metriky pro sales (FR-12.1) = Grafana dashboard nad Postgres (aktivace profilů, fit confirmation rate, pokrytí brandů, retence) — bez samostatné BI platformy v MVP.

## 7. Bezpečnost a GDPR v deploymentu

- Data výhradně v EU (Hetzner FSN1/NBG1, Sentry EU, PostHog EU); DPA uzavřít s Hetznerem, Sentry, PostHogem, Codemagicem.
- TLS všude (Cloudflare edge + origin certifikáty), HSTS.
- Šifrování at rest: LUKS volume + aplikační šifrování sloupců s měrami.
- Self-service export a smazání účtu = API endpointy od MVP (ne ruční proces).
- **Penetrační test ročně** (NFR) — rozpočtová položka, ~5–15 k€ dle rozsahu.
- Secrets v GitHub Actions Environments + na serverech přes SOPS/age šifrovaný `.env` (bez Vaultu — další služba na údržbu).

## 8. Náklady

### 8.1 Měsíční provoz — MVP (ceny ověřit při objednávce, Hetzner ceník se mění)

| Položka | Služba | ~€/měs |
|---|---|---|
| Load balancer | Hetzner LB11 | 6 |
| 2× app server | CPX31 (4 vCPU, 8 GB) | 32 |
| DB server | CPX41 (8 vCPU, 16 GB) + 100 GB volume | 35 |
| Zálohy VM (snapshoty) | +20 % ceny serverů | 13 |
| Staging | CPX21 | 9 |
| Object storage | zálohy + bundly | 6 |
| Sentry Team | | 24 |
| Codemagic | free tier → placený až při růstu | 0–30 |
| PostHog EU, Grafana Cloud, Cloudflare, UptimeRobot | free tiery | 0 |
| Transakční e-mail (Resend/Postmark) | sdílení profilů, účty | 14 |
| Doména, drobnosti | | 3 |
| **Celkem MVP** | | **~140–170** |

### 8.2 Měsíční provoz — design point (1 M profilů, 10 M dop./měs, Phase 2–3)

| Položka | ~€/měs |
|---|---|
| 3–4× app server (CPX41) | 90–120 |
| DB: CCX dedikovaný + read replika | 150–250 |
| LB, storage, zálohy | 40 |
| SaaS (Sentry, PostHog, Codemagic nad free tier, e-mail) | 150–250 |
| Retailer portál + web app (Phase 2/3, další 1–2 VM) | 30–60 |
| **Celkem** | **~600–900** |

### 8.3 Jednorázové / roční náklady

| Položka | Cena | Poznámka |
|---|---|---|
| Apple Developer Program | 99 $/rok | nutné pro TestFlight i App Store |
| Google Play Console | 25 $ jednorázově | |
| Penetrační test | 5–15 k€/rok | NFR z PRD; první před launchem P1 |
| Počáteční setup infry + CI/CD | ~10–14 dev-dní | viz §9 |
| Právní: DPA, cookie/consent review 3 trhů | dle právníka | souvisí s R10 z PRD, mimo infra rozpočet |

**Co v nákladech není:** vývoj samotné aplikace, datové operace (ingestion P1 brandů je dle PRD kritická cesta a lidská práce), marketing, právní služby.

## 9. Postup nasazení (váže se na P0/P1 z PRD)

| Krok | Obsah | Odhad |
|---|---|---|
| 1. Účty a základy | Hetzner projekt, Cloudflare, domény, GitHub org, Apple/Google účty (Apple review účtu trvá dny — začít hned), Sentry/PostHog EU | 1–2 dny |
| 2. Základní infra | VM, privátní síť, LB, LUKS volumes, hardening, staging | 2–3 dny |
| 3. CI/CD backend | Actions pipeline, registry, rolling deploy, Alembic migrace | 2 dny |
| 4. DB + zálohy | Postgres, pgBackRest do Object Storage, restore test | 1–2 dny |
| 5. CI/CD mobil | Codemagic, fastlane, podpisové certifikáty, TestFlight/Play internal | 2–3 dny |
| 6. Observabilita | Sentry, Grafana Cloud, uptime alerty, scrubbing middleware | 1–2 dny |
| 7. Data pipeline | ingestion joby, validace/kvaranténa, bundle publikace na CDN | v rámci P0 vývoje |
| 8. Go-live P1 | staged rollout ve storech, phased release, sledování fit-confirmation metriky | průběžně |

Kroky 1–6 dohromady **~10–14 dev-dní** a mohou běžet souběžně s vývojem P0 (datový model a matching engine infrastrukturu neblokují — vyvíjí se lokálně).

## 10. Rizika deploymentu a mitigace

| Riziko | Mitigace |
|---|---|
| Self-managed Postgres bez ops člověka (nejslabší místo návrhu) | pgBackRest s testovaným restore, alerty na replikaci/disk, runbook; úniková cesta: přesun na managed Postgres (Aiven/Scaleway, EU) = změna connection stringu, ne architektury |
| App Store / Play review zdrží launch | první submission s předstihem (beta build), review guidelines na sběr tělesných měr popsat v review notes; Apple si vyžádá privacy nutrition labels |
| Codemagic free tier přestane stačit | placený tier ~30–100 $/měs, alternativa GitHub Actions macOS runnery (dražší na minutu) |
| Výpadek Hetzner regionu | zálohy v druhém regionu; DR = obnovit stack z Terraform/compose + pgBackRest, RTO ~pár hodin — pro MVP přijatelné, multi-region až Phase 3 |
| Scraping size guidů (R3 z PRD) | ingestion joby respektují robots.txt a rate limity; per-retailer terms review je právní úkol před P0 koncem |

## 11. Otevřené body k rozhodnutí (menší, nezdržují start)

1. **Název domény** a e-mailová infrastruktura firmy.
2. **Terraform vs. dokumentovaný ruční setup** — doporučuji lehký Terraform (jen VM/LB/síť), ~1 den navíc, zaplatí se při DR.
3. **Retence záloh** — návrh: 30 dní denních, 12 měsíců měsíčních; potvrdit proti právním požadavkům.
4. **Push notifikace** — FCM + APNs (zdarma) stačí pro MVP; potvrdit, že FCM (Google) nevadí v privacy postoji (data v notifikacích nikdy neobsahují míry).
5. **Kdy zavést ClickHouse** pro log doporučení — návrh: až nad ~30 M záznamů, tj. Phase 2+.

---
*Dokument navazuje na WhatSize PRD v1.0 (27. 8. 2026). Ceny Hetzneru a SaaS ověřit při objednávce.*
