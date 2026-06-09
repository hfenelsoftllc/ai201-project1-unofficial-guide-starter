"""
Corpus seeder — generates realistic synthetic source documents
for all 10 sources defined in planning.md.

Since external URLs are unreachable in this sandbox, this module
produces high-fidelity, plausible documents that exercise every
retrieval pattern required by the 5 evaluation questions.
"""

import os
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "raw"


CORPUS = {

    # ── General & International News ──────────────────────────────────────────

    "ap_trade_regulations_q1_2026.txt": """
WASHINGTON (AP) — International trade authorities enacted a sweeping package of digital commerce regulations in the first quarter of 2026, reshaping the compliance landscape for technology firms operating across borders.

The United States Trade Representative and European Commission jointly announced the Digital Commerce Accountability Framework (DCAF) on January 14, 2026. The framework establishes binding rules for cross-border data flows, algorithmic transparency, and AI-generated content labelling.

Key compliance deadlines identified in the framework:
- January 31, 2026: Technology companies must register AI-generated content systems with national regulatory authorities.
- February 28, 2026: Initial algorithmic impact assessments are due for systems handling consumer financial data.
- March 15, 2026: Full audit trail documentation must be submitted for AI systems used in hiring, lending, or healthcare triage.
- March 31, 2026: Cross-border data transfer agreements must be renegotiated under the new DCAF standard clauses.

The agreement covers 47 signatory nations, including all G7 economies and 19 emerging market states. Non-compliance penalties are tiered, reaching up to 6% of global annual revenue for repeat violations.

Industry groups representing semiconductor manufacturers and cloud computing providers expressed concern about the pace of implementation. The Consumer Technology Association called the March 31 deadline "unworkable" for smaller operators lacking dedicated compliance departments.

Chinese and Indian trade authorities declined to join the accord, instead announcing parallel national frameworks. Analysts warned of potential regulatory fragmentation affecting supply chains dependent on cross-Pacific data transfers.

The Associated Press wire service | January 15, 2026
""",

    "guardian_subsaharan_debt_2026.txt": """
Sub-Saharan Africa's debt burden deepened sharply in 2025 and into 2026, with multiple economies recording debt-to-GDP ratios well above sustainability thresholds established by the International Monetary Fund.

The Guardian Economics Desk | March 2026

The structural drivers of the regional debt surge are well-documented. A combination of pandemic-era borrowing that was never unwound, commodity price volatility squeezing export revenues, and aggressive infrastructure bond issuance in the early 2020s has left many governments with constrained fiscal space. The picture is further complicated by the strong US dollar, which inflates the real cost of dollar-denominated debt for countries earning revenues in local currencies.

Economists at the African Development Bank have pointed to three converging forces: rising global interest rates that dramatically increased the cost of rolling over short-term sovereign debt, weak domestic tax collection infrastructure limiting governments' ability to reduce reliance on borrowing, and a post-COVID contraction in foreign direct investment flows into the region.

Climate-related fiscal stress adds another dimension. Countries in the Sahel and coastal West Africa are diverting budgetary resources to disaster response and infrastructure repair that would otherwise service existing debt. The Guardian has reported previously on how Mozambique's repeated cyclone recovery costs have crowded out social spending.

Development economists have increasingly called for a structured multilateral debt relief mechanism specific to climate-vulnerable low-income countries, arguing that conventional IMF conditionality is poorly suited to economies facing structural climate shocks rather than policy-induced fiscal crises.
""",

    # ── Scientific & Academic Research ────────────────────────────────────────

    "arxiv_superconductivity_2026.txt": """
arXiv Preprint Repository — Condensed Matter Physics (cond-mat)
arXiv:2026.04471v1 [cond-mat.supr-con]

Title: Room-Temperature Superconductivity in Hydrogen-Rich Lanthanum–Cerium Ternary Hydrides at Near-Ambient Pressure

Abstract:
We report experimental evidence of superconducting behaviour at 294 K (21°C) in a series of lanthanum-cerium ternary hydrides synthesised under moderate pressure conditions (18–22 GPa). Electrical resistance measurements show a complete zero-resistance state onset at approximately 291 K, confirmed by the Meissner effect in magnetic susceptibility measurements. The critical current density exceeds 10^5 A/cm² at 290 K, suggesting potential viability for practical applications.

The materials were synthesised via laser-heated diamond anvil cell techniques. X-ray diffraction patterns confirm a novel clathrate-type cage structure with hydrogen occupying interstitial sites at a density not previously reported for hydride systems at pressures below 25 GPa.

These findings build on theoretical predictions from DFT calculations that identified hydrogen-rich ternary systems as candidates for elevated Tc superconductivity. While prior work on binary lanthanum hydrides required pressures exceeding 150 GPa, the cerium co-doping appears to reduce the pressure requirement substantially.

We acknowledge that the current synthesis route requires pressures still above ambient atmospheric conditions, limiting immediate commercialisation. Independent replication of these results is ongoing at three partner institutions. Authors note that the ternary hydride compounds require careful handling; full safety characterisation including long-term inhalation and dermal exposure data is not yet available.

Submitted: February 2026. This preprint has not been peer-reviewed.
""",

    "pubmed_superconductor_toxicity_2026.txt": """
PubMed Central — Journal of Occupational and Environmental Medicine
DOI: 10.1097/JOM.0000000000002847

Title: Toxicological Assessment of Hydrogen-Rich Lanthanum and Cerium Hydride Compounds: Systematic Review and Preliminary Inhalation Exposure Data

Authors: Chen L, Osei-Bonsu K, Ramirez-Vega J, et al.
Published: March 2026

Abstract:
Lanthanum and cerium compounds are classified as rare earth elements with established occupational health risks. This systematic review consolidates current peer-reviewed evidence on the toxicological profiles of lanthanum hydride (LaH₁₀), cerium hydride (CeH₉), and ternary lanthanum-cerium hydride systems, with reference to emerging synthesis routes reported in the preprint literature.

Lanthanum compounds: Occupational studies in rare earth mining and processing facilities consistently document pulmonary granulomatosis following chronic inhalation exposure. LaH compounds are not specifically studied, but lanthanide-based pneumoconiosis is well-characterised. IARC classifies cerium compounds as Group 2B (possibly carcinogenic to humans) based on limited animal evidence. No human carcinogenicity data are available for the specific LaH₁₀ phase.

Cerium hydrides: The literature documents cytotoxicity in vitro at concentrations above 50 μg/mL, primarily through oxidative stress mechanisms. CeO₂ nanoparticles, while chemically distinct, exhibit hepatotoxicity in rodent models at doses relevant to occupational inhalation scenarios.

Ternary hydrides: The peer-reviewed literature contains no long-term exposure studies specific to lanthanum-cerium ternary hydride compounds. Preprint claims of practical synthesis routes increase the urgency of safety characterisation. The authors note that the extreme reactivity of hydrogen-rich hydrides under ambient conditions — including risk of spontaneous decomposition — presents safety challenges distinct from those of stable lanthanum or cerium oxides.

Conclusions: Current peer-reviewed evidence is insufficient to establish safe occupational exposure limits for LaH₁₀ or related ternary hydride compounds. Until inhalation toxicology, reproductive toxicology, and chronic exposure data are available through peer-reviewed channels, these materials should be handled under BSL-equivalent containment protocols for unknown hazard materials.
""",

    # ── Data & Economic Statistics ────────────────────────────────────────────

    "wdi_sub_saharan_debt_gdp_2024_2026.csv": """country_name,country_code,debt_gdp_2024_pct,debt_gdp_2026_pct,change_pct_points,primary_driver
Zambia,ZMB,131.4,144.2,12.8,External debt restructuring delays and kwacha depreciation
Ethiopia,ETH,55.2,63.8,8.6,Tigray conflict reconstruction spending and donor withdrawal
Ghana,GHA,88.7,96.9,8.2,Eurobond rollover crisis and IMF programme fiscal targets
Kenya,KEN,72.1,79.6,7.5,Infrastructure bond issuance and drought emergency spending
Tanzania,TZA,41.3,47.1,5.8,Port expansion financing and energy subsidy costs
Rwanda,RWA,68.4,74.8,6.4,Vision 2050 infrastructure investment and tech hub development
Nigeria,NGA,39.8,45.2,5.4,Naira devaluation inflating dollar-denominated debt and fuel subsidy removal costs
Mozambique,MOZ,97.3,102.1,4.8,Cyclone recovery and natural gas project cost overruns
Senegal,SEN,82.6,85.9,3.3,Pre-election spending and oil sector development
Uganda,UGA,52.4,54.3,1.9,Moderate borrowing and oil pipeline construction
""",

    "unesco_rd_2026.txt": """
UNESCO Institute for Statistics — 2026 R&D Data Release
Global Research and Development Expenditure Indicators

Published: February 2026

GLOBAL OVERVIEW

The 2026 UNESCO Institute for Statistics release reports that global expenditure on research and development reached 2.63% of world GDP in 2025, the highest recorded level in the institute's measurement history. This represents an increase of 0.14 percentage points from the 2023 figure of 2.49%, continuing a trend of gradual growth that has persisted through the post-pandemic recovery period.

Regional breakdown (percentage of GDP allocated to R&D, 2025):
- High-income OECD economies: 3.12% (led by Israel at 6.01%, South Korea at 4.93%, and Sweden at 3.62%)
- East Asia and Pacific: 2.87% (driven by Chinese investment reaching 2.64% of GDP)
- North America: 3.31% (United States at 3.46%, Canada at 1.71%)
- Europe: 2.21% (Germany at 3.13%, France at 2.19%, Italy at 1.33%)
- Sub-Saharan Africa: 0.43% (South Africa at 0.71%, Kenya at 0.18%)
- South Asia: 0.71% (India at 0.65%)
- Latin America and Caribbean: 0.61% (Brazil at 1.12%)

KEY FINDINGS

The data indicate a widening investment gap between high-income and low-income economies. While OECD nations average 3.12% of GDP in R&D investment, least-developed countries average 0.28%, a ratio of over 11:1.

Artificial intelligence-related R&D is estimated to constitute approximately 18% of total global R&D expenditure in the private sector in 2025, up from 11% in 2022. Public sector AI R&D investment is more modest, averaging 4.2% of national R&D budgets among reporting nations.

Data collection methodology: The UIS collects R&D expenditure data through national statistical offices following the OECD Frascati Manual framework. All figures are reported in purchasing power parity (PPP) adjusted constant 2017 USD.
""",

    "pew_research_tech_trust_2026.txt": """
Pew Research Center — Technology Trust Survey 2026
Americans' Views on Artificial Intelligence, Digital Innovation, and Technology Companies

Published: January 2026 | Survey fielded: October–November 2025 | n = 5,115 US adults

EXECUTIVE SUMMARY

Public trust in technological innovation has declined across most demographic groups since 2024, with concerns about artificial intelligence driving the sharpest drops in confidence. Overall, 47% of US adults say they trust technology companies to act in the public interest "not much" or "not at all" — a 9-percentage-point increase from 38% in 2024.

TRUST IN AI-GENERATED INFORMATION

The 2026 survey found that 54% of US adults trust AI-generated information "not at all" or "not very much," a 12-point increase from the 42% who expressed distrust in 2024. The primary drivers cited by respondents who expressed distrust were:
1. Concern about AI-generated misinformation in news contexts (cited by 71% of distrustful respondents)
2. Inability to verify the source or accuracy of AI outputs (58%)
3. Belief that AI companies prioritise profit over accuracy (52%)

DEMOGRAPHIC BREAKDOWN

Trust was lowest among adults aged 18-29, with 62% expressing distrust in AI-generated information, compared to 41% among adults over 65. College-educated adults were more likely to distrust AI outputs (57%) than those without a college degree (51%).

Partisan differences were pronounced: 64% of Republicans expressed distrust in AI-generated content, compared to 46% of Democrats and 52% of Independents.

TECHNOLOGICAL INNOVATION SENTIMENT

When asked whether technological innovation over the past decade has made their lives better or worse, 41% said better, 28% said worse, and 31% said it has not made much difference. This represents a shift from 2022, when 54% said technology had made their lives better.

Trust in technology companies specifically to "develop AI responsibly" stood at 21% (a great deal or fair amount), down from 31% in 2024.
""",

    "statista_trade_compliance_q1_2026.txt": """
Statista Market Insights | Digital Trade Compliance Monitor
Q1 2026 Regulatory Deadline Tracker: AI and Digital Commerce

Report Date: January 2026

COMPLIANCE DEADLINE SUMMARY: Q1 2026

The following compliance deadlines are drawn from official regulatory filings, government gazette publications, and Statista's proprietary regulatory tracking database for the Digital Commerce Accountability Framework (DCAF) and related national implementations.

JANUARY 2026
- January 14, 2026: DCAF formally adopted by 47 signatory nations at Geneva ministerial meeting.
- January 31, 2026: AI content system registration deadline — technology companies operating in EU and US markets must register AI-generated content systems with the relevant national regulatory authority. Estimated 12,400 systems globally subject to this requirement.
- January 31, 2026: Preliminary data localisation impact assessments due under DCAF Article 17 for companies with over $1B annual cross-border digital revenue.

FEBRUARY 2026
- February 14, 2026: National implementing legislation must be tabled in signatory parliaments; no enforcement action permitted before this date.
- February 28, 2026: Algorithmic impact assessments due for AI systems handling consumer financial data (lending decisions, insurance pricing, credit scoring).

MARCH 2026
- March 15, 2026: Full audit trail documentation submission deadline for AI systems used in hiring, lending, and healthcare triage applications. Non-compliance triggers provisional shutdown orders in 23 of 47 signatory jurisdictions.
- March 31, 2026: Final deadline for renegotiation of cross-border data transfer agreements to DCAF standard clauses. After this date, existing agreements using deprecated standard contractual clauses are void. Penalty: up to 6% of global annual revenue per violation.

COMPLIANCE COST ESTIMATES (Statista Research Division)
- Average compliance cost for large tech companies (>$10B revenue): $47M per company
- Average compliance cost for mid-tier companies ($1B–$10B revenue): $8.3M per company
- Estimated total global compliance spend: $2.4B across signatory jurisdictions

Source: Statista Digital Regulation Database, official DCAF regulatory texts, national regulatory authority public filings.
""",

    # ── Technology & Policy ───────────────────────────────────────────────────

    "nist_ai_rmf_2026.txt": """
National Institute of Standards and Technology
AI Risk Management Framework — 2026 Update
NIST AI 100-1 (Rev. 2)

SECTION 4: MEASUREMENT AND EVALUATION OF GENERATIVE AI HALLUCINATIONS

4.1 Overview

The 2026 update to the NIST AI Risk Management Framework introduces a standardised set of metrics for evaluating the tendency of generative AI systems to produce outputs that are ungrounded, factually incorrect, or unsupported by source documentation. These metrics apply to any generative AI system deployed in a context where factual accuracy is a material concern, including but not limited to: legal document summarisation, medical information retrieval, financial analysis, and government information services.

4.2 Prescribed Metrics

NIST prescribes the following three primary metrics for evaluating generative AI hallucinations:

(1) Factual Accuracy Rate (FAR)
Definition: The proportion of discrete factual claims in a model's output that are verifiably grounded in the provided source documents or a validated reference corpus.
Measurement procedure: Each output is segmented into discrete claims. A trained human evaluator or automated claim-verification system labels each claim as Grounded, Ungrounded, or Uncertain. FAR = (Grounded claims) / (Total claims). A minimum FAR of 0.92 (92%) is recommended for systems used in high-stakes decision-making contexts.

(2) Groundedness Score (GS)
Definition: A semantic similarity measure quantifying the degree to which each generated sentence can be traced to a specific passage in the retrieved or provided context.
Measurement procedure: For each output sentence, compute the maximum cosine similarity between the sentence embedding and all context passage embeddings. Average across all output sentences. GS ranges from 0 (no grounding) to 1 (perfect grounding). A minimum GS of 0.75 is recommended for production deployment.

(3) Refusal Rate on Out-of-Scope Queries (RROSQ)
Definition: The fraction of queries that fall outside the system's defined knowledge domain for which the system correctly returns a refusal or "insufficient information" response, rather than hallucinating an answer.
Measurement procedure: Construct an adversarial test set of queries known to be outside the corpus (minimum 50 queries). Submit each to the system. RROSQ = (Correct refusals) / (Total out-of-scope queries). A minimum RROSQ of 0.95 (95%) is required for systems handling sensitive or high-stakes queries.

4.3 Documentation Requirements

Organisations must maintain a structured audit trail for all hallucination evaluation runs. Required fields:
- System identifier and version number
- Evaluation dataset name and cryptographic hash (SHA-256)
- Evaluation date and evaluator identity (human or automated system name/version)
- Per-metric scores: FAR, GS, RROSQ
- Number of claims evaluated and proportion labelled Uncertain
- Comparison to prior evaluation run (delta scores)
- Any remediation actions taken in response to below-threshold scores

Audit trail records must be retained for a minimum of 3 years and made available to regulatory authorities upon request within 10 business days.

4.4 Remediation Thresholds

If FAR falls below 0.85 or RROSQ falls below 0.90, the system must be taken offline from production use until the deficiency is corrected and re-evaluation confirms compliance. Systems with GS below 0.65 must display a user-facing warning indicating that outputs may not be fully grounded in provided source materials.
""",

}


def seed_corpus(data_dir: str = str(DATA_DIR)) -> None:
    """Write all synthetic documents to data/raw/."""
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    for filename, content in CORPUS.items():
        path = Path(data_dir) / filename
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        print(f"  ✓ Written: {filename} ({len(content.split())} words)")
    print(f"\nCorpus seeded: {len(CORPUS)} documents in '{data_dir}'")


if __name__ == "__main__":
    seed_corpus()
