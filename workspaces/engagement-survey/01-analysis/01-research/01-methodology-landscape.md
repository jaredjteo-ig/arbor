# Methodology landscape

Three industry-standard engagement-survey methodologies. The product
should let HR pick from these as starter templates AND author their
own. Each comes with a different cadence, depth, and analytical model.

## Gallup Q12

**What it is.** A 12-statement instrument Gallup has run on >35M
employees globally since 1998. Each statement is rated on a 5-point
Likert (Strongly Disagree → Strongly Agree). Aggregated into a single
"engagement index" plus per-question heat-maps.

**The 12 statements (paraphrased — Gallup's exact wording is
copyrighted)**:

1. I know what is expected of me at work.
2. I have the materials and equipment I need to do my work right.
3. At work, I have the opportunity to do what I do best every day.
4. In the last seven days, I have received recognition or praise for
   doing good work.
5. My supervisor, or someone at work, seems to care about me as a person.
6. There is someone at work who encourages my development.
7. At work, my opinions seem to count.
8. The mission/purpose of my company makes me feel my job is important.
9. My associates or fellow employees are committed to doing quality work.
10. I have a best friend at work.
11. In the last six months, someone at work has talked to me about my progress.
12. This last year, I have had opportunities at work to learn and grow.

**Why it matters.** Gallup's 2026 report headlined that only 20% of
the global workforce felt engaged in 2025. Q12 is the de-facto
benchmark; HR teams expect it on the shopping list.

**IP risk.** Gallup's exact phrasing IS copyrighted and trademarked.
The platform should ship a paraphrased "Q12-style" template with a
visible attribution disclaimer; HR who want the certified instrument
can license it from Gallup separately.

**Cadence.** Annual or twice-yearly. Not for pulse use — too long.

## Trust Index™ Survey (Great Place to Work)

**What it is.** A ~60-statement Likert instrument across five pillars:
**Credibility, Respect, Fairness, Pride, Camaraderie** — plus open
text. Used as the primary input to GPTW certification.

**Why it matters.** GPTW certification is a known badge in the SG SME
ecosystem; ranking on lists like Singapore's Best Workplaces drives
recruiting. HR who want to pursue certification need a tool that
captures Trust Index pillars natively.

**IP risk.** GPTW licenses the instrument; we paraphrase and provide
a "Trust Index pillars" template with the five categories as the
default sections.

**Cadence.** Annual.

## Pulse surveys

**What it is.** 3-7 questions, sent monthly/biweekly/weekly. Used to
catch early signals of disengagement before the annual survey window.

**Common pulse questions.**

- "How happy are you at work this week?" (1-5 emoji scale)
- "I felt valued for my contributions this week." (Likert)
- "What's getting in your way right now?" (free text)
- "Do you have what you need to do your best work?" (Likert)
- "Would you recommend this team as a place to work?" (eNPS 0-10)

**Why it matters.** Annual surveys are lagging indicators. Pulse
surveys give HR a near-real-time read; the trend matters more than
the absolute score.

**IP risk.** None — generic pattern.

**Cadence.** Recurring (monthly default). Schedule + auto-launch is a
must.

## Comparison table

| Methodology | Cadence | Length        | Aggregation            | Buyer signal               |
| ----------- | ------- | ------------- | ---------------------- | -------------------------- |
| Gallup Q12  | Annual  | 12 Q (5 min)  | Engagement index 0-100 | Benchmark-credibility play |
| Trust Index | Annual  | 60 Q (15 min) | 5 pillars + open text  | Certification path         |
| Pulse       | Monthly | 3-7 Q (90s)   | Trend over time        | Operational signal         |

## What to ship in v1

- **Pulse-first** — the recurring 90-second survey that produces a
  trend line. This is where the daily product value lives.
- **Q12 paraphrase template** in the library — buyers expect it.
- **Trust Index pillars template** — five sections, paraphrased
  prompts, useful for once-a-year deep dives.
- **Custom builder** — HR composes their own from scratch.

## What to ship later (v2+)

- eNPS as a first-class metric (single-question version of pulse).
- Sentiment analysis on free-text responses (LLM-driven).
- Comparison to industry / size benchmarks (requires anonymized
  cross-tenant data — needs a separate privacy review).
- Integrations: Slack, Teams, calendar reminders.
