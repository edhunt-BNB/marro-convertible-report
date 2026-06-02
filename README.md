# Marro D2MS — Convertible Dispositions Reports

Auto-generated daily reports from the Marro MaxContact telesales data in Airtable.

## Reports

| Report | Description |
|--------|-------------|
| **Short NI** | Records where Result Code = NI and Talk Time < 1 min. Categories: Critical (<30s) and Review (30-60s). |
| **Callbacks** | Records where Result Code = CALLBACK. Categories: Short (<1m), Medium (1-3m), Long (3m+). |
| **Other Convertibles** | All other Convertible result codes (TOOEXP, PAYISSUE, FUSSY, MEDIFOOD, HEALTH). Same talk time tiers as Callbacks. |

## Setup

### 1. Create Airtable PAT

1. Go to https://airtable.com/create/tokens
2. Create a new token with `data.records:read` scope
3. Grant access to the Marro base (`appc3AWUlFaHlmdWk`)

### 2. Add GitHub Secret

1. Go to your repo Settings > Secrets and variables > Actions
2. Add a new secret: `AIRTABLE_PAT` = your token from step 1

### 3. Enable GitHub Pages

1. Go to repo Settings > Pages
2. Set Source to "Deploy from a branch"
3. Set Branch to `main` and folder to `/docs`
4. Save

### 4. Run

Reports generate automatically at 9am London time daily via GitHub Actions.

To trigger manually: Actions tab > "Generate Marro D2MS Reports" > Run workflow.

## Local Development

```bash
AIRTABLE_PAT=pat... python3 generate_reports.py
# Output goes to docs/
```

## File Structure

```
generate_reports.py      # Main generator script
templates/               # HTML templates with %%PLACEHOLDER%% tokens
  index.html             # Hub page
  ni.html                # Short NI report template
  callbacks.html         # Callbacks report template
  convertibles.html      # Other Convertibles report template
docs/                    # Generated output (served by GitHub Pages)
  index.html
  ni.html
  callbacks.html
  convertibles.html
.github/workflows/
  generate-reports.yml   # Daily cron schedule
```
