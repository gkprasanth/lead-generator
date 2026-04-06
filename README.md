# VocaSpeak AI Lead Generator

This repo contains a practical lead-generation toolkit for finding schools that are likely to buy **VocaSpeak AI** (voice-first vocabulary and speaking improvement).

You do **not** need to feed lead lists into it — the bot discovers leads from live web search results and then enriches/scored them.

## What this does

- Searches the web for school websites using targeted B2B queries.
- Scrapes publicly available pages for contact emails and phone numbers.
- Scores lead relevance using your ICP keywords (CBSE, international, Cambridge/IB, AI-focused, language labs, soft skills, etc.).
- Exports all leads to `output/leads.csv` (ready for Google Sheets).
- Provides ready-to-use outreach templates in `templates/email_templates.md`.

## Quick start

```bash
python3 lead_generator.py --max-results 80 --country-focus "India"
```

Output appears in `output/leads.csv`.

## Upload to Google Sheets

1. Open Google Sheets.
2. File → Import → Upload.
3. Choose `output/leads.csv`.
4. Select “Insert new sheet”.

## CLI options

```bash
python3 lead_generator.py \
  --max-results 100 \
  --country-focus "India" \
  --extra-query "ai centric school language lab" \
  --min-score 35
```

### Flags

- `--max-results`: Number of search results to process (default: `60`)
- `--country-focus`: Country or region text to include in queries (default: `India`)
- `--extra-query`: Additional custom query (can be repeated)
- `--min-score`: Filter low-quality leads from export (default: `25`)

## Compliance reminders

- Use only publicly available contact information.
- Respect each website’s terms of use and robots policies.
- Verify consent and anti-spam rules before sending campaigns (GDPR/CAN-SPAM/local regulations).

## Troubleshooting

- If `Leads generated: 0`, the scraper likely could not access search/website pages from your current network.
- Retry with:
  - higher `--max-results`
  - a few `--extra-query` values
  - a network/VPS where outbound web requests are allowed
