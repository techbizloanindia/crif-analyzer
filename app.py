"""
CRIF High Mark Credit PDF Analyzer
Workflow: Upload PDF → JSON → Dashboard → Excel Export
"""

import streamlit as st
import pandas as pd
import json
import io
import re

from parser import CrifParser
from excel_generator import generate_excel_report

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CRIF High Mark Credit Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }

/* ── Title ── */
.title-banner {
    background: linear-gradient(135deg, #0f2444 0%, #1a3a6b 50%, #0f2444 100%);
    padding: 32px 40px;
    border-radius: 20px;
    text-align: center;
    margin-bottom: 28px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.25);
    border: 1px solid rgba(255,255,255,0.08);
}
.title-banner h1 { margin:0; font-weight:800; font-size:2.4rem; color:#fff; letter-spacing:-0.5px; }
.title-banner p  { margin:10px 0 0; font-weight:300; font-size:1rem; color:rgba(255,255,255,0.8); }

/* ── Step Flow ── */
.step-flow {
    display: flex; align-items: center; justify-content: center;
    gap: 8px; margin: 18px 0 30px; flex-wrap: wrap;
}
.step-box {
    background: rgba(46,117,182,0.15); border: 1px solid rgba(46,117,182,0.4);
    border-radius: 10px; padding: 8px 16px; font-size: 0.82rem;
    font-weight: 600; color: #2e75b6;
}
.step-arrow { color: #8c96a3; font-size: 1.1rem; }

/* ── KPI Cards ── */
.kpi-card {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128,128,128,0.2);
    border-radius: 16px; padding: 22px;
    text-align: center; margin-bottom: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.05);
    transition: all 0.3s ease;
}
.kpi-card:hover { transform: translateY(-4px); box-shadow: 0 12px 32px rgba(0,0,0,0.12); border-color: #2e75b6; }
.kpi-title { font-size:0.78rem; font-weight:700; color:#8c96a3; text-transform:uppercase; letter-spacing:1.2px; margin-bottom:8px; }
.kpi-value { font-size:1.9rem; font-weight:800; margin-bottom:5px; }
.kpi-desc  { font-size:0.75rem; color:#8c96a3; }
.kpi-green  { color:#10b981; }
.kpi-blue   { color:#2e75b6; }
.kpi-red    { color:#ef4444; }
.kpi-orange { color:#f39c12; }

/* ── Profile Card ── */
.profile-card {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128,128,128,0.2);
    border-radius: 16px; padding: 24px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.05);
}
.profile-header {
    font-size:1.1rem; font-weight:700;
    border-bottom: 2px solid #2e75b6;
    padding-bottom: 10px; margin-bottom: 18px;
}
.profile-row {
    display: flex; justify-content: space-between;
    padding: 9px 0; border-bottom: 1px solid rgba(128,128,128,0.1);
    font-size: 0.9rem;
}
.profile-label { font-weight:600; color:#8c96a3; }
.profile-val   { font-weight:500; }

/* ── Insight Cards ── */
.insight-card {
    background: var(--secondary-background-color);
    border-left: 4px solid #2e75b6;
    border-radius: 10px; padding: 14px 18px;
    margin-bottom: 10px; font-size:0.9rem;
}
.finding-positive { border-left-color: #10b981; }
.finding-negative { border-left-color: #ef4444; }
.finding-neutral  { border-left-color: #8c96a3; }

/* ── Risk Badge ── */
.risk-badge {
    display: inline-block;
    padding: 4px 14px; border-radius: 20px;
    font-size: 0.8rem; font-weight: 700; color: #fff;
    margin-left: 8px;
}

/* ── Section Header ── */
.section-header {
    font-size: 1.1rem; font-weight: 700;
    border-bottom: 2px solid rgba(128,128,128,0.15);
    padding-bottom: 8px; margin: 20px 0 14px;
}

/* ── Summary Box ── */
.summary-box {
    background: linear-gradient(135deg, rgba(46,117,182,0.08) 0%, rgba(15,36,68,0.08) 100%);
    border: 1px solid rgba(46,117,182,0.3);
    border-radius: 14px; padding: 22px 26px; margin-bottom: 22px;
    line-height: 1.7; font-size: 0.95rem;
}

/* ── Status Pills ── */
.pill-active   { background:#dcfce7; color:#166534; padding:2px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
.pill-closed   { background:#f3f4f6; color:#374151; padding:2px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
.pill-overdue  { background:#fee2e2; color:#991b1b; padding:2px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
.pill-written  { background:#fef3c7; color:#92400e; padding:2px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }

/* ── Warning / Info banners ── */
.warn-box {
    background:#fef3c7; border:1px solid #fbbf24; border-radius:12px;
    padding:16px 20px; margin:16px 0; font-size:0.9rem; color:#78350f;
}
.info-box {
    background:rgba(46,117,182,0.08); border:1px solid rgba(46,117,182,0.3);
    border-radius:12px; padding:16px 20px; margin:16px 0; font-size:0.9rem;
}
</style>
""", unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────────

def safe_float(v) -> float:
    if v is None: return 0.0
    cleaned = re.sub(r"[^\d\.]", "", str(v))
    try: return float(cleaned) if cleaned else 0.0
    except: return 0.0

def fmt_inr(v) -> str:
    f = safe_float(v)
    if f == 0.0: return "₹0"
    return f"₹{f:,.0f}"

def pill(status: str) -> str:
    sl = str(status).lower()
    if "active" in sl:   return f'<span class="pill-active">{status}</span>'
    if "closed" in sl:   return f'<span class="pill-closed">{status}</span>'
    if "written" in sl or "write" in sl: return f'<span class="pill-written">{status}</span>'
    if "overdue" in sl or "settled" in sl: return f'<span class="pill-overdue">{status}</span>'
    return f'<span class="pill-closed">{status}</span>'

def ndash(v) -> str:
    return v if v and str(v).strip() not in ["", "N/A", "-", "None", "nan"] else "—"

# ── No sidebar — API removed ─────────────────────────────────────────────────

# ── Title Banner ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="title-banner">
  <h1>📊 CRIF High Mark Credit Analyzer</h1>
  <p>Upload your credit report PDF · View the extracted data as JSON · Export to Excel</p>
</div>
""", unsafe_allow_html=True)

# ── File Upload ────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "📂 Upload CRIF High Mark Credit Report PDF",
    type=["pdf"],
    help="Upload the unencrypted PDF downloaded from CRIF High Mark portal.",
)

if uploaded_file is None:
    st.markdown("""
    <div style="text-align:center; padding:50px 30px; border:2px dashed rgba(128,128,128,0.3); border-radius:20px; margin:20px 0;">
        <div style="font-size:3rem; margin-bottom:16px;">📂</div>
        <h3 style="margin:0 0 10px;">Drop your CRIF PDF here</h3>
        <p style="color:#8c96a3; max-width:480px; margin:0 auto; font-size:0.9rem;">
            The analyzer will extract all credit records, personal information, inquiry history,
            and DPD data directly from the PDF — and generate a full Excel report.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Parse PDF ─────────────────────────────────────────────────────────────────
st.markdown("---")

with st.spinner("🔍 Parsing PDF and extracting data..."):
    try:
        parser_obj = CrifParser(uploaded_file)
        parsed_data = parser_obj.parse()
    except Exception as e:
        import traceback
        st.error(f"❌ Failed to parse PDF: {e}")
        with st.expander("Technical Details"):
            st.code(traceback.format_exc())
        st.stop()

# Unpack parsed fields
score        = parsed_data.get("credit_score")
personal     = parsed_data.get("personal_info", {})
metrics      = parsed_data.get("summary_metrics", {})
accounts     = parsed_data.get("accounts", [])
inquiries    = parsed_data.get("inquiries", [])
derived      = parsed_data.get("derived_attributes", {})
income_band  = parsed_data.get("income_band", "-")
metadata     = parsed_data.get("metadata", {})
raw_pages    = parsed_data.get("raw_text_by_page", {})

# ── Data Quality Gate ──────────────────────────────────────────────────────────
has_data = (
    score is not None
    or len(accounts) > 0
    or any(v and v not in ["N/A", "-", ""] for v in [personal.get("Name"), personal.get("PAN")])
)

if not has_data:
    st.warning(
        "⚠️ **No meaningful data could be extracted from this PDF.**\n\n"
        "Possible reasons:\n"
        "- PDF is scanned/image-based (not text-based)\n"
        "- PDF is password-protected\n"
        "- File is not a CRIF High Mark credit report\n\n"
        "Please upload a **text-based, unencrypted** CRIF credit report PDF."
    )
    with st.expander("🔍 Raw Extracted Text", expanded=True):
        for pg, txt in list(raw_pages.items())[:3]:
            st.markdown(f"**Page {pg}:**")
            st.text(txt[:1500] if txt else "(Empty page — image-based PDF)")
    st.stop()

# ── Build Exports ──────────────────────────────────────────────────────────────
with st.spinner("📊 Generating Excel report..."):
    try:
        excel_bytes = generate_excel_report(parsed_data)
    except Exception as ex:
        excel_bytes = b""
        st.warning(f"Excel generation failed: {ex}")

# Clean JSON shown in the dashboard — strips bulky raw text/table dumps,
# keeping only the real structured data extracted from the PDF.
clean_json = {k: v for k, v in parsed_data.items() if k not in ["raw_text_by_page", "tables_by_page"]}

safe_name = (personal.get("Name") or "Report").replace(" ", "_")

# ── Top Action Bar ──────────────────────────────────────────────────
ref_no = metadata.get("ref_number") or "N/A"
rep_date = metadata.get("report_date") or "N/A"
display_name = ndash(personal.get("Name"))

col_hdr, col_xl = st.columns([3, 1])
with col_hdr:
    st.markdown(f"### 👤 {display_name}")
    st.markdown(f"Ref: `{ref_no}` &nbsp;|&nbsp; Date: `{rep_date}`", unsafe_allow_html=True)
with col_xl:
    if excel_bytes:
        st.download_button("⬇️ Download Excel Report", data=excel_bytes,
            file_name=f"CRIF_Report_{safe_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)
    else:
        st.warning("Excel report could not be generated from this PDF.")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_exec, tab_accts, tab_inq, tab_charts, tab_json = st.tabs([
    "📊 Executive Summary",
    "🏦 Accounts & Details",
    "🔍 Inquiries",
    "📈 Charts",
    "📄 JSON Data",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Executive Summary
# ─────────────────────────────────────────────────────────────────────────────
with tab_exec:
    # ── Plain-language Report Summary ─────────────────────────────────────────
    if score:
        if   score >= 750: s_rating, s_color = "Excellent", "#10b981"
        elif score >= 650: s_rating, s_color = "Good",      "#2ecc71"
        elif score >= 550: s_rating, s_color = "Fair",      "#f39c12"
        else:              s_rating, s_color = "Poor",      "#ef4444"
        score_txt = f"<b>{score}</b> (<span style='color:{s_color};font-weight:700'>{s_rating}</span>)"
    else:
        score_txt = "<b>not detected</b>"

    sum_name      = ndash(personal.get("Name"))
    sum_total     = metrics.get("total_accounts", len(accounts))
    sum_active    = metrics.get("active_accounts", 0)
    sum_closed    = metrics.get("closed_accounts", 0)
    sum_overdue_n = metrics.get("overdue_accounts", 0)
    sum_out       = fmt_inr(metrics.get("total_outstanding", "0"))
    sum_ovd       = fmt_inr(metrics.get("total_overdue", "0"))
    sum_wo        = derived.get("written_off_accounts", 0)
    sum_inq_total = len(inquiries)
    sum_inq_6m    = derived.get("inquiries_6m", 0)
    sum_hist      = ndash(derived.get("credit_history_length", "—"))

    # One-line health verdict based purely on the extracted figures
    if sum_overdue_n == 0 and sum_wo == 0:
        verdict = "✅ Clean record — no overdue or written-off accounts found."
    else:
        flags = []
        if sum_overdue_n: flags.append(f"{sum_overdue_n} overdue account(s)")
        if sum_wo:        flags.append(f"{sum_wo} written-off account(s)")
        verdict = "⚠️ Needs attention — " + ", ".join(flags) + "."

    st.markdown(f"""
    <div class="summary-box">
      <div style="font-size:1.05rem;font-weight:700;margin-bottom:10px;">📋 Report Summary</div>
      <div style="margin-bottom:10px;">
        <b>{sum_name}</b> has a CRIF credit score of {score_txt}.
        The report lists <b>{sum_total}</b> credit account(s) —
        <b>{sum_active}</b> active and <b>{sum_closed}</b> closed —
        with a total outstanding balance of <b>{sum_out}</b>
        (of which <b>{sum_ovd}</b> is currently overdue).
        Credit history length: <b>{sum_hist}</b>.
        Lender inquiries on record: <b>{sum_inq_total}</b> ({sum_inq_6m} in the last 6 months).
      </div>
      <div style="font-weight:600;">{verdict}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── JSON summary — overview of every extracted section ────────────────────
    section_labels = {
        "metadata":           "Report Metadata",
        "personal_info":      "Personal Info",
        "loan_application":   "Loan Application",
        "credit_score":       "Credit Score",
        "score_factors":      "Score Factors",
        "income_band":        "Income Band",
        "summary_metrics":    "Summary Metrics",
        "derived_attributes": "Derived Attributes",
        "accounts":           "Accounts",
        "inquiries":          "Inquiries",
        "status_details":     "Status Details",
    }

    def _json_size(v):
        if isinstance(v, list): return f"{len(v)} record(s)"
        if isinstance(v, dict): return f"{len(v)} field(s)"
        if v is None or str(v).strip() in ["", "-", "N/A", "None", "nan"]: return "—"
        return str(v)

    json_rows = "".join(
        f'<div class="profile-row"><span class="profile-label">{section_labels.get(k, k)}</span>'
        f'<span class="profile-val">{_json_size(v)}</span></div>'
        for k, v in clean_json.items()
    )
    st.markdown(f"""
    <div class="summary-box">
      <div style="font-size:1.05rem;font-weight:700;margin-bottom:10px;">🧾 Extracted JSON — Section Overview</div>
      {json_rows}
      <div style="font-size:0.8rem;color:#8c96a3;margin-top:8px;">
        Full data is available in the 📄 JSON Data tab.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Credit Score Gauge ────────────────────────────────────────────────────
    col_gauge, col_pers = st.columns([1, 1])

    with col_gauge:
        if score:
            ratio        = max(0.0, min(1.0, (score - 300) / 600))
            active_dash  = ratio * 314.16
            if score >= 750: sc, label = "#27ae60", "EXCELLENT"
            elif score >= 650: sc, label = "#2ecc71", "GOOD"
            elif score >= 550: sc, label = "#f39c12", "FAIR"
            else: sc, label = "#e74c3c", "POOR"
            score_disp = score
        else:
            active_dash, sc, label, score_disp = 0, "#95a5a6", "NOT DETECTED", "N/A"

        st.markdown(f"""
        <div class="profile-card" style="text-align:center;">
          <div class="profile-header">CRIF Credit Score</div>
          <svg width="240" height="155" viewBox="0 0 240 155" style="display:block;margin:auto">
            <path d="M20,130 A100,100 0 0,1 220,130" fill="none" stroke="rgba(128,128,128,0.15)" stroke-width="20" stroke-linecap="round"/>
            <path d="M20,130 A100,100 0 0,1 220,130" fill="none" stroke="{sc}" stroke-width="20" stroke-linecap="round" stroke-dasharray="{active_dash} 314.16"/>
            <text x="120" y="88" text-anchor="middle" font-size="42" font-family="Outfit,sans-serif" font-weight="800" fill="currentColor">{score_disp}</text>
            <text x="120" y="118" text-anchor="middle" font-size="15" font-family="Outfit,sans-serif" font-weight="700" fill="{sc}">{label}</text>
          </svg>
          <div style="font-size:0.78rem;color:#8c96a3;margin-top:8px;">Scale: 300 – 900</div>
        </div>
        """, unsafe_allow_html=True)

    with col_pers:
        fields = [
            ("Full Name",       personal.get("Name")),
            ("Father's Name",   personal.get("Father")),
            ("PAN Number",      personal.get("PAN")),
            ("Aadhaar",         personal.get("Aadhaar")),
            ("Date of Birth",   personal.get("DOB")),
            ("Gender",          personal.get("Gender")),
            ("Mobile",          personal.get("Mobile")),
            ("Email",           personal.get("Email")),
        ]
        rows_html = "".join(
            f'<div class="profile-row"><span class="profile-label">{lbl}</span>'
            f'<span class="profile-val">{ndash(val)}</span></div>'
            for lbl, val in fields
        )
        addr = ndash(personal.get("Address"))
        if addr != "—":
            rows_html += (
                f'<div class="profile-row"><span class="profile-label">Address</span>'
                f'<span class="profile-val" style="max-width:240px;text-align:right">{addr}</span></div>'
            )
        st.markdown(f"""
        <div class="profile-card">
          <div class="profile-header">Personal Information</div>
          {rows_html}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Credit Portfolio Summary</div>', unsafe_allow_html=True)
    k1, k2, k3, k4, k5, k6 = st.columns(6)

    total_accts    = metrics.get("total_accounts", len(accounts))
    active_accts   = metrics.get("active_accounts", 0)
    closed_accts   = metrics.get("closed_accounts", 0)
    overdue_accts  = metrics.get("overdue_accounts", 0)
    total_out      = metrics.get("total_outstanding", "0")
    total_ovd      = metrics.get("total_overdue", "0")
    secured_c      = metrics.get("secured_accounts", 0)
    unsecured_c    = metrics.get("unsecured_accounts", 0)

    out_str = fmt_inr(total_out)
    ovd_str = fmt_inr(total_ovd)
    ovd_class = "kpi-red" if safe_float(total_ovd) > 0 else "kpi-green"

    kpi_data = [
        (k1, "Total Accounts",   total_accts,  "kpi-blue",   "Reported accounts"),
        (k2, "Active Accounts",  active_accts, "kpi-green",  f"Closed: {closed_accts}"),
        (k3, "Overdue Accounts", overdue_accts, "kpi-red" if overdue_accts else "kpi-green", "Accounts in delay"),
        (k4, "Outstanding",      out_str,      "kpi-blue",   "Total unpaid balance"),
        (k5, "Overdue Amount",   ovd_str,      ovd_class,    "Past-due balance"),
        (k6, "Credit Mix",       f"{secured_c}S / {unsecured_c}U", "kpi-orange", "Secured / Unsecured"),
    ]
    for col, title, value, cls, desc in kpi_data:
        with col:
            st.markdown(f"""
            <div class="kpi-card">
              <div class="kpi-title">{title}</div>
              <div class="kpi-value {cls}">{value}</div>
              <div class="kpi-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)



# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Accounts & Details
# ─────────────────────────────────────────────────────────────────────────────
with tab_accts:
    st.markdown('<div class="section-header">Credit Accounts & Trade Lines</div>', unsafe_allow_html=True)

    if not accounts:
        st.warning("No account records were extracted from this PDF.")
    else:
        df = pd.DataFrame(accounts)

        # ── Filters ──────────────────────────────────────────────────────────
        with st.expander("🔎 Filter & Search Accounts", expanded=False):
            fc1, fc2, fc3, fc4 = st.columns(4)

            all_lenders = sorted(df["Lender"].dropna().unique().tolist()) if "Lender" in df.columns else []
            all_types   = sorted(df["Account Type"].dropna().unique().tolist()) if "Account Type" in df.columns else []
            all_status  = sorted(df["Status"].dropna().unique().tolist()) if "Status" in df.columns else []

            with fc1:
                sel_lender = st.multiselect("Lender", all_lenders, key="fil_lender")
            with fc2:
                sel_type   = st.multiselect("Account Type", all_types, key="fil_type")
            with fc3:
                sel_status = st.multiselect("Status", all_status, key="fil_status")
            with fc4:
                search_txt = st.text_input("🔍 Search (any field)", key="fil_search")

        # Apply filters
        df_f = df.copy()
        if sel_lender: df_f = df_f[df_f["Lender"].isin(sel_lender)]
        if sel_type:   df_f = df_f[df_f["Account Type"].isin(sel_type)]
        if sel_status: df_f = df_f[df_f["Status"].isin(sel_status)]
        if search_txt:
            mask = df_f.apply(lambda row: row.astype(str).str.contains(search_txt, case=False, na=False).any(), axis=1)
            df_f = df_f[mask]

        st.caption(f"Showing **{len(df_f)}** of **{len(df)}** accounts")

        # Preferred column order
        preferred = [
            "Lender","Account Number","Account Type","Status",
            "Date Opened","Last Reported",
            "Current Balance","Overdue Amount","Credit Limit/Sanctioned","High Credit",
            "Asset Classification","Security",
            "Interest Rate","Installment Amount",
            "Write-off Amount","WO/Settled Status",
            "Last Payment","Ownership","Occupation",
            "DPD History / Payment History",
        ]
        present_pref = [c for c in preferred if c in df_f.columns]
        extra        = [c for c in df_f.columns if c not in preferred]
        df_show      = df_f[present_pref + extra].copy()

        # Serial number — 1, 2, 3… in the order rows are shown (resets with filters)
        df_show.insert(0, "Sr. No.", range(1, len(df_show) + 1))

        st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
            height=520,
            column_config={
                "Sr. No.": st.column_config.NumberColumn("Sr. No.", width="small"),
            },
        )

        # Quick stats below table
        st.markdown('<div class="section-header">Filtered Account Statistics</div>', unsafe_allow_html=True)
        s1, s2, s3, s4 = st.columns(4)
        total_bal_f  = df_f["Current Balance"].apply(safe_float).sum() if "Current Balance" in df_f.columns else 0
        total_ovd_f  = df_f["Overdue Amount"].apply(safe_float).sum() if "Overdue Amount" in df_f.columns else 0
        total_lim_f  = df_f["Credit Limit/Sanctioned"].apply(safe_float).sum() if "Credit Limit/Sanctioned" in df_f.columns else 0
        total_emi_f  = df_f["Installment Amount"].apply(safe_float).sum() if "Installment Amount" in df_f.columns else 0

        for col, label, val, cls in [
            (s1, "Total Balance (Filtered)", fmt_inr(total_bal_f), "kpi-blue"),
            (s2, "Total Overdue (Filtered)", fmt_inr(total_ovd_f), "kpi-red" if total_ovd_f > 0 else "kpi-green"),
            (s3, "Total Limit (Filtered)",   fmt_inr(total_lim_f), "kpi-orange"),
            (s4, "Total Monthly EMI",        fmt_inr(total_emi_f), "kpi-green"),
        ]:
            with col:
                st.markdown(f"""
                <div class="kpi-card">
                  <div class="kpi-title">{label}</div>
                  <div class="kpi-value {cls}">{val}</div>
                </div>""", unsafe_allow_html=True)

with tab_inq:
    st.markdown('<div class="section-header">Lender Inquiry History</div>', unsafe_allow_html=True)
    st.write("Hard inquiries by financial institutions — each inquiry can impact your credit score.")

    if not inquiries:
        st.info("No inquiry records were extracted from this PDF.")
    else:
        df_inq = pd.DataFrame(inquiries)
        cols_inq = ["Inquiry Date","Inquirer","Purpose","Amount"]
        pres_inq = [c for c in cols_inq if c in df_inq.columns]
        df_inq   = df_inq[pres_inq]

        # Date-range filter
        with st.expander("🔎 Filter Inquiries", expanded=False):
            search_inq = st.text_input("Search inquiries", key="inq_search")

        if search_inq:
            mask = df_inq.apply(lambda r: r.astype(str).str.contains(search_inq, case=False, na=False).any(), axis=1)
            df_inq = df_inq[mask]

        df_inq = df_inq.copy()
        df_inq.insert(0, "Sr. No.", range(1, len(df_inq) + 1))

        st.dataframe(
            df_inq,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Sr. No.": st.column_config.NumberColumn("Sr. No.", width="small"),
            },
        )
        st.caption(f"Showing {len(df_inq)} inquiry record(s).")

        # Inquiry summary KPIs
        inq_6m  = derived.get("inquiries_6m", 0)
        iq1, iq2, iq3 = st.columns(3)
        with iq1:
            st.markdown(f"""<div class="kpi-card">
              <div class="kpi-title">Total Inquiries</div>
              <div class="kpi-value kpi-blue">{len(inquiries)}</div>
              <div class="kpi-desc">All reported</div>
            </div>""", unsafe_allow_html=True)
        with iq2:
            st.markdown(f"""<div class="kpi-card">
              <div class="kpi-title">Last 6 Months</div>
              <div class="kpi-value {'kpi-red' if inq_6m > 4 else 'kpi-orange' if inq_6m > 2 else 'kpi-green'}">{inq_6m}</div>
              <div class="kpi-desc">{'⚠️ High' if inq_6m > 4 else '⚡ Moderate' if inq_6m > 2 else '✅ Normal'}</div>
            </div>""", unsafe_allow_html=True)
        with iq3:
            unique_inqrs = len(set(i.get("Inquirer","") for i in inquiries if i.get("Inquirer","")))
            st.markdown(f"""<div class="kpi-card">
              <div class="kpi-title">Unique Lenders</div>
              <div class="kpi-value kpi-orange">{unique_inqrs}</div>
              <div class="kpi-desc">Distinct inquiring institutions</div>
            </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — Charts & Visualizations
# ─────────────────────────────────────────────────────────────────────────────
with tab_charts:
    try:
        import plotly.graph_objects as go
        import plotly.express as px
        from plotly.subplots import make_subplots
        plotly_ok = True
    except ImportError:
        plotly_ok = False

    if not plotly_ok:
        st.warning("Plotly is not installed. Run `pip install plotly` to enable charts.")
    elif not accounts:
        st.info("Charts will appear here once account data is extracted from the uploaded PDF.")
    else:
        df_chart = pd.DataFrame(accounts)

        PALETTE = ["#2e75b6","#10b981","#f39c12","#ef4444","#8b5cf6","#06b6d4","#f97316","#ec4899"]

        # ── Row 1: Account Mix Donut + Active/Closed Donut ────────────────────
        c1_r1, c2_r1 = st.columns(2)

        with c1_r1:
            if "Account Type" in df_chart.columns:
                type_counts = df_chart["Account Type"].value_counts().reset_index()
                type_counts.columns = ["Account Type","Count"]
                fig_donut = go.Figure(go.Pie(
                    labels=type_counts["Account Type"],
                    values=type_counts["Count"],
                    hole=0.55,
                    marker_colors=PALETTE,
                    textinfo="label+percent",
                    textfont_size=11,
                ))
                fig_donut.update_layout(
                    title="Account Type Mix",
                    showlegend=True,
                    height=340,
                    margin=dict(l=20,r=20,t=50,b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_donut, use_container_width=True)

        with c2_r1:
            if "Status" in df_chart.columns:
                status_counts = df_chart["Status"].value_counts().reset_index()
                status_counts.columns = ["Status","Count"]
                status_colors = {
                    "Active":"#10b981","Closed":"#8c96a3",
                    "Written Off":"#ef4444","Settled":"#f39c12",
                }
                colors_list = [status_colors.get(s, "#2e75b6") for s in status_counts["Status"]]
                fig_status = go.Figure(go.Pie(
                    labels=status_counts["Status"],
                    values=status_counts["Count"],
                    hole=0.55,
                    marker_colors=colors_list,
                    textinfo="label+value",
                    textfont_size=11,
                ))
                fig_status.update_layout(
                    title="Account Status Distribution",
                    showlegend=True,
                    height=340,
                    margin=dict(l=20,r=20,t=50,b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_status, use_container_width=True)

        # ── Row 2: Outstanding Balance per Lender ─────────────────────────────
        if "Current Balance" in df_chart.columns and "Lender" in df_chart.columns:
            df_bal = df_chart.copy()
            df_bal["_Balance"] = df_bal["Current Balance"].apply(safe_float)
            df_bal_grp = df_bal.groupby("Lender", as_index=False)["_Balance"].sum()
            df_bal_grp = df_bal_grp[df_bal_grp["_Balance"] > 0].sort_values("_Balance", ascending=True)

            if not df_bal_grp.empty:
                fig_bar = go.Figure(go.Bar(
                    x=df_bal_grp["_Balance"],
                    y=df_bal_grp["Lender"],
                    orientation="h",
                    marker_color="#2e75b6",
                    text=[fmt_inr(v) for v in df_bal_grp["_Balance"]],
                    textposition="auto",
                ))
                fig_bar.update_layout(
                    title="Outstanding Balance by Lender",
                    xaxis_title="Balance (₹)",
                    height=max(300, len(df_bal_grp) * 42 + 80),
                    margin=dict(l=20,r=20,t=50,b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_bar, use_container_width=True)

        # ── Row 3: Outstanding vs Overdue Stacked ─────────────────────────────
        c1_r3, c2_r3 = st.columns(2)

        with c1_r3:
            if "Current Balance" in df_chart.columns and "Overdue Amount" in df_chart.columns:
                df_so = df_chart.copy()
                df_so["_Balance"]  = df_so["Current Balance"].apply(safe_float)
                df_so["_Overdue"]  = df_so["Overdue Amount"].apply(safe_float)
                df_so["_Lender"]   = df_so.get("Lender", pd.Series(["Unknown"]*len(df_so)))
                df_so = df_so[df_so["_Balance"] > 0].head(12)

                if not df_so.empty:
                    fig_stack = go.Figure()
                    fig_stack.add_trace(go.Bar(name="Outstanding", x=df_so["_Lender"], y=df_so["_Balance"], marker_color="#2e75b6"))
                    fig_stack.add_trace(go.Bar(name="Overdue",     x=df_so["_Lender"], y=df_so["_Overdue"], marker_color="#ef4444"))
                    fig_stack.update_layout(
                        barmode="overlay", title="Outstanding vs Overdue",
                        xaxis_tickangle=-35, height=340,
                        margin=dict(l=20,r=20,t=50,b=60),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig_stack, use_container_width=True)

        with c2_r3:
            # Credit Utilization Gauge
            total_outstanding_val = safe_float(metrics.get("total_outstanding", 0))
            total_limit_val       = safe_float(metrics.get("sanctioned_amount", 0))
            if total_limit_val == 0:
                total_limit_val = df_chart["Credit Limit/Sanctioned"].apply(safe_float).sum() if "Credit Limit/Sanctioned" in df_chart.columns else 0

            util_pct = (total_outstanding_val / total_limit_val * 100) if total_limit_val > 0 else 0

            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=round(util_pct, 1),
                number={"suffix": "%", "font": {"size": 32}},
                title={"text": "Credit Utilization", "font": {"size": 14}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1},
                    "bar":  {"color": "#2e75b6"},
                    "steps": [
                        {"range": [0,   30], "color": "#dcfce7"},
                        {"range": [30,  60], "color": "#fef3c7"},
                        {"range": [60, 100], "color": "#fee2e2"},
                    ],
                    "threshold": {"line": {"color":"#ef4444","width":3}, "thickness":0.75, "value":80}
                }
            ))
            fig_gauge.update_layout(
                height=340,
                margin=dict(l=20,r=20,t=50,b=20),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

        # ── Row 4: Inquiry Timeline ────────────────────────────────────────────
        if inquiries:
            df_inq_ch = pd.DataFrame(inquiries)
            if "Inquiry Date" in df_inq_ch.columns:
                from datetime import datetime
                def _parse_dt(s):
                    if not s or s in ["-","N/A"]: return None
                    for fmt in ["%d-%m-%Y","%d/%m/%Y","%Y-%m-%d","%d-%b-%Y"]:
                        try: return datetime.strptime(str(s).strip(), fmt)
                        except: pass
                    return None

                df_inq_ch["_Date"] = df_inq_ch["Inquiry Date"].apply(_parse_dt)
                df_inq_ch = df_inq_ch.dropna(subset=["_Date"])

                if not df_inq_ch.empty:
                    df_inq_ch["_Month"] = df_inq_ch["_Date"].apply(lambda d: d.strftime("%Y-%m"))
                    monthly_inq = df_inq_ch.groupby("_Month").size().reset_index(name="Count")
                    monthly_inq = monthly_inq.sort_values("_Month")

                    fig_inq = go.Figure(go.Bar(
                        x=monthly_inq["_Month"], y=monthly_inq["Count"],
                        marker_color="#8b5cf6",
                        text=monthly_inq["Count"], textposition="auto",
                    ))
                    fig_inq.update_layout(
                        title="Inquiry Frequency by Month",
                        xaxis_title="Month", yaxis_title="Inquiries",
                        height=300, margin=dict(l=20,r=20,t=50,b=40),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig_inq, use_container_width=True)

        # ── Row 5: Account Opening Timeline ───────────────────────────────────
        if "Date Opened" in df_chart.columns:
            from datetime import datetime
            def _parse_open(s):
                if not s or s in ["-","N/A"]: return None
                for fmt in ["%d-%m-%Y","%d/%m/%Y","%Y-%m-%d","%d-%b-%Y"]:
                    try: return datetime.strptime(str(s).strip(), fmt)
                    except: pass
                return None

            df_chart["_Opened"] = df_chart["Date Opened"].apply(_parse_open)
            df_open = df_chart.dropna(subset=["_Opened"])

            if not df_open.empty:
                df_open["_Year"] = df_open["_Opened"].apply(lambda d: str(d.year))
                year_counts = df_open.groupby("_Year").size().reset_index(name="Accounts Opened")
                year_counts = year_counts.sort_values("_Year")

                fig_open = go.Figure(go.Scatter(
                    x=year_counts["_Year"], y=year_counts["Accounts Opened"],
                    mode="lines+markers+text",
                    text=year_counts["Accounts Opened"],
                    textposition="top center",
                    line=dict(color="#10b981", width=2),
                    marker=dict(size=8, color="#10b981"),
                    fill="tozeroy", fillcolor="rgba(16,185,129,0.08)",
                ))
                fig_open.update_layout(
                    title="Account Opening History by Year",
                    xaxis_title="Year", yaxis_title="Accounts Opened",
                    height=300, margin=dict(l=20,r=20,t=50,b=40),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_open, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — JSON Data
# ─────────────────────────────────────────────────────────────────────────────
with tab_json:
    st.markdown('<div class="section-header">📄 Extracted JSON Data</div>', unsafe_allow_html=True)
    st.write("Your uploaded PDF has been converted to JSON. Every value below is sourced directly from the document.")

    st.caption(
        f"📑 {len(accounts)} accounts  |  🔍 {len(inquiries)} inquiries  |  "
        f"💳 Credit score: {score if score else '—'}"
    )

    jc1, jc2 = st.columns(2)
    with jc1:
        scope = st.radio("Show", ["Full report", "Single section"], horizontal=True)
    with jc2:
        fmt = st.radio("Format", ["Tree view", "Raw JSON text"], horizontal=True)

    if scope == "Single section":
        sec = st.selectbox("Section", list(clean_json.keys()))
        data_to_show = clean_json.get(sec, {})
    else:
        data_to_show = clean_json

    if fmt == "Tree view":
        st.json(data_to_show)
    else:
        st.code(
            json.dumps(data_to_show, indent=2, ensure_ascii=False, default=str),
            language="json",
        )

# ─────────────────────────────────────────────────────────────────────────────
# Debug Expander
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("🔧 Debug: Raw PDF Text", expanded=False):
    st.write(f"Pages: {len(raw_pages)} | Accounts: {len(accounts)} | Inquiries: {len(inquiries)}")
    for pg, txt in raw_pages.items():
        with st.expander(f"Page {pg} ({len(txt)} chars)", expanded=False):
            st.text(txt[:3000] + ("…" if len(txt) > 3000 else "") if txt else "(Empty)")
