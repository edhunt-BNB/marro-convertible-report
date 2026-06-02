#!/usr/bin/env python3
"""
Marro D2MS Report Generator
Pulls data from Airtable and generates 3 HTML reports + index hub page.
Designed to run daily via GitHub Actions at 9am London time.

Usage:
  AIRTABLE_PAT=pat... python3 generate_reports.py

Output:
  docs/index.html          - Hub page linking all reports
  docs/ni.html             - Short NI Dispositions (<1 min talk time)
  docs/callbacks.html      - Callback Dispositions
  docs/convertibles.html   - Other Convertible Dispositions
"""

import json, os, sys, urllib.request, urllib.parse
from datetime import datetime, timezone

# --- Config ---
BASE_ID = "appc3AWUlFaHlmdWk"
TABLE_ID = "tblvKTDt7r9JYHqGO"
AIRTABLE_API = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")

# Field IDs for reference (used in Airtable API field selection)
FIELDS = [
    "First Name", "Last Name", "Phone Num", "CatName",
    "Agent First Name", "Agent Last Name", "Talk Time",
    "Lead Total Attempts", "last_call_date", "import_date",
    "Import Week", "Day Of Week", "Is Final", "Result Code",
    "Result Outcome"
]


def fetch_all_records(pat):
    """Fetch all records from Airtable with pagination."""
    headers = {"Authorization": f"Bearer {pat}"}
    all_records = []
    offset = None

    while True:
        params = {"pageSize": "100"}
        for f in FIELDS:
            params.setdefault("fields[]", [])
        # Build URL with field params
        url = AIRTABLE_API + "?"
        parts = [f"pageSize=100"]
        for f in FIELDS:
            parts.append(f"fields[]={urllib.parse.quote(f)}")
        if offset:
            parts.append(f"offset={offset}")
        url = AIRTABLE_API + "?" + "&".join(parts)

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())

        for rec in data.get("records", []):
            fields = rec.get("fields", {})
            all_records.append({
                "id": rec["id"],
                "firstName": fields.get("First Name", ""),
                "lastName": fields.get("Last Name", ""),
                "phone": fields.get("Phone Num", ""),
                "catName": fields.get("CatName", ""),
                "agentFirst": fields.get("Agent First Name", ""),
                "agentLast": fields.get("Agent Last Name", ""),
                "talkTime": fields.get("Talk Time", 0) or 0,
                "attempts": fields.get("Lead Total Attempts", 0) or 0,
                "lastCallDate": fields.get("last_call_date", ""),
                "importDate": fields.get("import_date", ""),
                "importWeek": fields.get("Import Week", ""),
                "dayOfWeek": fields.get("Day Of Week", ""),
                "isFinal": bool(fields.get("Is Final")),
                "resultCode": fields.get("Result Code", ""),
                "resultOutcome": fields.get("Result Outcome", ""),
            })

        offset = data.get("offset")
        if not offset:
            break
        print(f"  Fetched {len(all_records)} records so far...")

    return all_records


def transform_record(r, flag_fn):
    """Transform a raw record into the shape expected by report templates."""
    tt = r.get("talkTime") or 0
    af = r.get("agentFirst", "") or ""
    al = r.get("agentLast", "") or ""
    rep = f"{af} {al}".strip()
    fn = r.get("firstName", "") or ""
    ln = r.get("lastName", "") or ""
    customer = f"{fn} {ln}".strip()

    lcd = r.get("lastCallDate", "")
    lcd_str = ""
    if lcd:
        try:
            dt = datetime.fromisoformat(lcd.replace("Z", "+00:00"))
            lcd_str = dt.strftime("%Y-%m-%d")
        except:
            lcd_str = str(lcd)[:10]

    imd = r.get("importDate", "")
    imd_str = ""
    if imd:
        try:
            dt = datetime.fromisoformat(imd.replace("Z", "+00:00"))
            imd_str = dt.strftime("%Y-%m-%d")
        except:
            imd_str = str(imd)[:10]

    return {
        "rep": rep,
        "customer": customer,
        "phone": r.get("phone", "") or "",
        "catName": r.get("catName", "") or "",
        "talkSeconds": tt,
        "attempts": r.get("attempts", 0) or 0,
        "lastCall": lcd_str,
        "importDate": imd_str,
        "importWeek": r.get("importWeek", "") or "",
        "dayOfWeek": r.get("dayOfWeek", "") or "",
        "isFinal": bool(r.get("isFinal")),
        "resultCode": r.get("resultCode", "") or "",
        "resultOutcome": r.get("resultOutcome", "") or "",
        "flag": flag_fn(tt),
    }


def ni_flag(tt):
    if tt < 30: return "CRITICAL"
    if tt < 60: return "REVIEW"
    if tt < 180: return "SHORT"
    if tt < 300: return "MEDIUM"
    return "LONG"

def callback_flag(tt):
    if tt < 60: return "SHORT"
    if tt < 180: return "MEDIUM"
    return "LONG"

# Same tiers for other convertibles
convertible_flag = callback_flag


# ============================================================
# HTML Templates — loaded from separate files or inline
# ============================================================

def get_css_common():
    """Shared CSS variables and base styles."""
    return r"""
:root {
  --bg:#faf9f7;--card:#fff;--border:#e8e5e0;
  --text:#2c1810;--text2:#6b5b50;--text3:#9b8b7f;
  --brown-800:#4a3728;--brown-600:#6b5b50;--brown-200:#d4c8bc;
  --amber:#d97706;--amber-light:#fef3c7;
  --green:#059669;--green-light:#d1fae5;
  --red:#dc2626;--red-light:#fee2e2;
  --blue:#2563eb;--purple:#7c3aed;--teal:#0d9488;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);font-size:13px;line-height:1.5}
.header{display:flex;align-items:center;justify-content:space-between;padding:20px 24px 16px;border-bottom:1px solid var(--border);background:var(--card)}
.header h1{font-size:1.15rem;font-weight:700;color:var(--brown-800)}
.header p{font-size:.78rem;color:var(--text2);margin-top:2px}
.btn{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border:1px solid var(--border);border-radius:6px;background:var(--card);color:var(--text);font-size:.78rem;cursor:pointer;transition:.15s}
.btn:hover{background:var(--bg)}.btn-ghost{border:none}
.stats-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:16px 24px}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.stat-card .label{font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.04em;color:var(--text3)}
.stat-card .value{font-size:1.6rem;font-weight:700;color:var(--brown-800);margin:2px 0}
.stat-card .sub{font-size:.72rem;color:var(--text2)}
.stat-card.warn{border-left:3px solid var(--red)}
.stat-card.short{border-left:3px solid var(--red)}
.stat-card.medium{border-left:3px solid var(--amber)}
.stat-card.long{border-left:3px solid var(--green)}
.toolbar{display:flex;align-items:center;gap:10px;padding:10px 24px;flex-wrap:wrap;background:var(--card);border-bottom:1px solid var(--border)}
.search-box{display:flex;align-items:center;gap:6px;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;flex:0 1 220px}
.search-box input{border:none;background:none;outline:none;font-size:.82rem;width:100%;color:var(--text)}
.search-box svg{flex-shrink:0;color:var(--text3)}
select{appearance:none;background:var(--bg) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%236b5b50'/%3E%3C/svg%3E") no-repeat right 10px center;border:1px solid var(--border);border-radius:6px;padding:6px 28px 6px 10px;font-size:.82rem;color:var(--text);cursor:pointer}
.filter-chips{display:flex;gap:4px}
.chip{padding:5px 12px;border-radius:20px;border:1px solid var(--border);background:var(--card);font-size:.78rem;cursor:pointer;transition:.15s}
.chip.active{background:var(--brown-800);color:#fff;border-color:var(--brown-800)}
.chip[data-flag="CRITICAL"].active,.chip[data-flag="SHORT"].active{background:var(--red);border-color:var(--red)}
.chip[data-flag="Review"].active,.chip[data-flag="MEDIUM"].active{background:var(--amber);border-color:var(--amber)}
.chip[data-flag="LONG"].active{background:var(--green);border-color:var(--green)}
.results-count{font-size:.78rem;color:var(--text3);margin-left:auto}
.tabs{display:flex;gap:0;border-bottom:2px solid var(--border);padding:0 24px;background:var(--card)}
.tab-btn{padding:10px 20px;font-size:.82rem;font-weight:600;border:none;background:none;color:var(--text2);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;transition:.15s}
.tab-btn.active{color:var(--brown-800);border-bottom-color:var(--brown-800)}
.panel{display:none;padding:20px 24px}.panel.active{display:block}
.chart-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
.chart-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px}
.chart-card h3{font-size:.82rem;font-weight:600;color:var(--brown-800);margin-bottom:8px}
.chart-container{width:100%;height:280px}
.rep-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px;margin-bottom:20px}
.rep-card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px;cursor:pointer;transition:.15s}
.rep-card:hover{border-color:var(--brown-800);box-shadow:0 2px 8px rgba(0,0,0,.06)}
.rep-name{font-size:.82rem;font-weight:700;color:var(--brown-800);margin-bottom:6px}
.rep-metrics{display:flex;gap:12px;margin-bottom:8px}
.metric{text-align:center}.mv{font-size:1rem;font-weight:700;color:var(--text)}.ml{font-size:.68rem;color:var(--text3)}
.short-metric .mv,.crit-metric .mv{color:var(--red)}
.bar{height:4px;background:var(--bg);border-radius:2px;overflow:hidden}
.bar-fill{height:100%;border-radius:2px}
.offenders{margin-top:20px}
.offenders h3{font-size:.88rem;font-weight:700;color:var(--brown-800);margin-bottom:12px}
table{width:100%;border-collapse:collapse;font-size:.78rem}
thead th{position:sticky;top:0;background:var(--bg);padding:8px 10px;text-align:left;font-weight:600;color:var(--text2);border-bottom:2px solid var(--border);cursor:pointer;white-space:nowrap;user-select:none}
thead th:hover{color:var(--brown-800)}
tbody td{padding:7px 10px;border-bottom:1px solid var(--border)}
tbody tr:hover{background:#f5f3f0}
.sort-arrow{font-size:.65rem;opacity:.4}
th.sorted .sort-arrow{opacity:1}
.crit,.flag-short{color:var(--red);font-weight:700}
.flag-medium{color:var(--amber);font-weight:700}
.flag-long{color:var(--green);font-weight:700}
.rep-badge{display:inline-block;padding:2px 8px;border-radius:4px;background:#f0ebe6;font-size:.75rem;font-weight:500}
.code-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.75rem;font-weight:600}
.code-TOOEXP{background:#dbeafe;color:#1e40af}.code-PAYISSUE{background:#fef3c7;color:#92400e}
.code-FUSSY{background:#fce7f3;color:#9d174d}.code-MEDIFOOD{background:#d1fae5;color:#065f46}
.code-HEALTH{background:#ede9fe;color:#5b21b6}
.table-wrap{overflow-x:auto}
.pagination{display:flex;align-items:center;justify-content:center;gap:8px;padding:16px}
.page-btn{padding:4px 12px;border:1px solid var(--border);border-radius:4px;background:var(--card);font-size:.78rem;cursor:pointer}
.page-btn.active{background:var(--brown-800);color:#fff;border-color:var(--brown-800)}
.page-btn:disabled{opacity:.4;cursor:default}
mark{background:#fde68a;padding:0 1px;border-radius:2px}
.nav-bar{display:flex;gap:0;background:var(--brown-800);padding:0 24px}
.nav-link{padding:12px 20px;font-size:.82rem;font-weight:600;color:rgba(255,255,255,.6);text-decoration:none;border-bottom:2px solid transparent;transition:.15s}
.nav-link:hover{color:#fff}
.nav-link.active{color:#fff;border-bottom-color:#fff}
@media(max-width:768px){.stats-row{grid-template-columns:repeat(2,1fr)}.chart-grid{grid-template-columns:1fr}.toolbar{flex-direction:column;align-items:stretch}}
"""


def get_nav_bar(active):
    """Navigation bar for switching between reports."""
    links = [
        ("index.html", "Hub"),
        ("ni.html", "Short NI"),
        ("callbacks.html", "Callbacks"),
        ("convertibles.html", "Other Convertibles"),
    ]
    html = '<div class="nav-bar">'
    for href, label in links:
        cls = ' active' if href.startswith(active) else ''
        html += f'<a class="nav-link{cls}" href="{href}">{label}</a>'
    html += '</div>'
    return html


def get_js_common():
    """Shared JS utility functions."""
    return r"""
function fmt(s) {
  if (s < 60) return '0:' + String(s).padStart(2,'0');
  var m = Math.floor(s/60), ss = s % 60;
  return m + ':' + String(ss).padStart(2,'0');
}
function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
var PAGE_SIZE = 50, currentPage = 1;

function goPage(p) { currentPage = p; renderRecords(); window.scrollTo(0, document.getElementById('panel-records').offsetTop); }

function switchTab(btn) {
  var btns = document.querySelectorAll('.tab-btn');
  var panels = document.querySelectorAll('.panel');
  for (var i=0;i<btns.length;i++) btns[i].classList.remove('active');
  for (var i=0;i<panels.length;i++) panels[i].classList.remove('active');
  btn.classList.add('active');
  document.getElementById('panel-'+btn.getAttribute('data-tab')).classList.add('active');
  if (btn.getAttribute('data-tab')==='records') renderRecords();
}

function sortBy(col) {
  if (sortCol===col) sortDir*=-1; else { sortCol=col; sortDir=1; }
  var ths = document.querySelectorAll('#panel-records th');
  for (var i=0;i<ths.length;i++) {
    ths[i].classList.toggle('sorted', ths[i].getAttribute('data-col')===col);
    var arrow = ths[i].querySelector('.sort-arrow');
    if (ths[i].getAttribute('data-col')===col) arrow.innerHTML = sortDir===1 ? '&#9650;' : '&#9660;';
  }
  renderRecords();
}

function renderPagination(totalItems) {
  var totalPages = Math.ceil(totalItems / PAGE_SIZE);
  var pag = document.getElementById('pagination');
  if (totalPages <= 1) { pag.innerHTML=''; return; }
  var ph = '<button class="page-btn" onclick="goPage('+(currentPage-1)+')"'+(currentPage===1?' disabled':'')+'>&lsaquo; Prev</button>';
  for (var i=1;i<=totalPages;i++) {
    if (i===1||i===totalPages||Math.abs(i-currentPage)<=2) ph+='<button class="page-btn'+(i===currentPage?' active':'')+'" onclick="goPage('+i+')">'+i+'</button>';
    else if (Math.abs(i-currentPage)===3) ph+='<span style="color:var(--text3)">&hellip;</span>';
  }
  ph+='<button class="page-btn" onclick="goPage('+(currentPage+1)+')"'+(currentPage===totalPages?' disabled':'')+'>Next &rsaquo;</button>';
  pag.innerHTML=ph;
}
"""


# ============================================================
# Report Generators - each reads its own template inline
# ============================================================

def generate_ni_report(records, gen_date):
    """Generate NI report HTML — all NI records, 5 talk-time tiers."""
    # Filter: Result Code = NI (all talk times)
    ni_records = [r for r in records if r.get("resultCode") == "NI"]
    transformed = [transform_record(r, ni_flag) for r in ni_records]
    data_json = json.dumps(transformed, separators=(",", ":"))
    total = len(transformed)

    # Read NI template
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "ni.html")
    with open(template_path, "r") as f:
        template = f.read()

    subtitle = f"{total} records where Result Code = NI across the full 3-month dataset | Updated {gen_date}"
    html = template.replace("%%DATA%%", data_json).replace("%%SUBTITLE%%", subtitle)
    return html, total


def generate_callbacks_report(records, gen_date):
    """Generate Callbacks report HTML."""
    cb_records = [r for r in records if r.get("resultCode") == "CALLBACK"]
    transformed = [transform_record(r, callback_flag) for r in cb_records]
    data_json = json.dumps(transformed, separators=(",", ":"))
    total = len(transformed)

    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "callbacks.html")
    with open(template_path, "r") as f:
        template = f.read()

    subtitle = f"{total} records where Result Code = CALLBACK across the full 3-month dataset | Updated {gen_date}"
    html = template.replace("%%DATA%%", data_json).replace("%%SUBTITLE%%", subtitle)
    return html, total


def generate_convertibles_report(records, gen_date):
    """Generate Other Convertibles report HTML."""
    conv_records = [
        r for r in records
        if r.get("resultOutcome") == "Convertible"
        and r.get("resultCode") not in ("NI", "CALLBACK")
    ]
    transformed = [transform_record(r, convertible_flag) for r in conv_records]
    data_json = json.dumps(transformed, separators=(",", ":"))
    total = len(transformed)

    # Count by code
    code_counts = {}
    for r in transformed:
        code_counts[r["resultCode"]] = code_counts.get(r["resultCode"], 0) + 1

    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "convertibles.html")
    with open(template_path, "r") as f:
        template = f.read()

    subtitle = f"{total} Convertible records (excl. NI &amp; Callback) across the full 3-month dataset | Updated {gen_date}"
    html = template.replace("%%DATA%%", data_json).replace("%%SUBTITLE%%", subtitle)
    return html, total, code_counts


def generate_index(gen_date, ni_count, cb_count, conv_count, conv_codes):
    """Generate the hub index page."""
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "index.html")
    with open(template_path, "r") as f:
        template = f.read()

    codes_html = ""
    for code, count in sorted(conv_codes.items(), key=lambda x: -x[1]):
        codes_html += f'<span class="code-badge code-{code}">{code}: {count}</span> '

    html = (template
        .replace("%%DATE%%", gen_date)
        .replace("%%NI_COUNT%%", str(ni_count))
        .replace("%%CB_COUNT%%", str(cb_count))
        .replace("%%CONV_COUNT%%", str(conv_count))
        .replace("%%CONV_CODES%%", codes_html))
    return html


def main():
    pat = os.environ.get("AIRTABLE_PAT")
    if not pat:
        print("ERROR: AIRTABLE_PAT environment variable not set.")
        print("Get your PAT from https://airtable.com/create/tokens")
        sys.exit(1)

    gen_date = datetime.now(timezone.utc).strftime("%d %B %Y")

    print(f"[{datetime.now().isoformat()}] Starting Marro D2MS report generation...")
    print(f"Fetching all records from Airtable...")
    records = fetch_all_records(pat)
    print(f"  Total records fetched: {len(records)}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Generating Short NI report...")
    ni_html, ni_count = generate_ni_report(records, gen_date)
    with open(os.path.join(OUTPUT_DIR, "ni.html"), "w") as f:
        f.write(ni_html)
    print(f"  -> {ni_count} records")

    print("Generating Callbacks report...")
    cb_html, cb_count = generate_callbacks_report(records, gen_date)
    with open(os.path.join(OUTPUT_DIR, "callbacks.html"), "w") as f:
        f.write(cb_html)
    print(f"  -> {cb_count} records")

    print("Generating Other Convertibles report...")
    conv_html, conv_count, conv_codes = generate_convertibles_report(records, gen_date)
    with open(os.path.join(OUTPUT_DIR, "convertibles.html"), "w") as f:
        f.write(conv_html)
    print(f"  -> {conv_count} records ({conv_codes})")

    print("Generating hub index page...")
    index_html = generate_index(gen_date, ni_count, cb_count, conv_count, conv_codes)
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w") as f:
        f.write(index_html)

    print(f"\n✓ All reports generated in {OUTPUT_DIR}/")
    print(f"  ni.html          ({ni_count} records)")
    print(f"  callbacks.html    ({cb_count} records)")
    print(f"  convertibles.html ({conv_count} records)")
    print(f"  index.html        (hub page)")


if __name__ == "__main__":
    main()
