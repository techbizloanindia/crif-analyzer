# 📊 CRIF High Mark Credit Analyzer

A powerful Streamlit web application that parses **CRIF High Mark credit report PDFs** and provides a rich interactive dashboard with charts, JSON data, and Excel export.

## ✨ Features

- **PDF Parsing** — Upload any CRIF High Mark credit report PDF and instantly extract all structured data
- **Executive Dashboard** — Credit score gauge, KPI cards, personal info, and a plain-language summary
- **Account Details** — Filterable table of all trade lines with balance, overdue, DPD history, and more
- **Inquiry History** — Full lender inquiry timeline with frequency charts
- **Interactive Charts** — Account mix, status distribution, outstanding vs overdue, credit utilization gauge, and inquiry timeline (powered by Plotly)
- **JSON Export** — View and copy the full structured JSON extracted from the PDF
- **Excel Export** — One-click download of a formatted multi-sheet Excel report

## 🚀 Quick Start

### ▶️ One-click (Windows — easiest)

Just **double-click `run.bat`**.

The script will automatically:
1. Check that Python is installed
2. Detect and **auto-install any missing modules** from `requirements.txt`
3. Launch the app and open it in your browser at `http://localhost:8501`

> No commands to type — if dependencies are missing the first time, they install themselves.

### 💻 Manual (any OS)

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/crif-analyzer.git
cd crif-analyzer

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## 🔐 Login Credentials

The app is protected by a login screen. Use the following credentials to sign in:

| Field | Value |
|-------|-------|
| **Username** | `crif.analyzer` |
| **Password** | `Credit.team@analyzer` |

> ⚠️ These are stored in `app.py`. Change them there if you need different access details.

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web UI framework |
| `pdfplumber` | PDF text extraction |
| `pandas` | Data manipulation |
| `plotly` | Interactive charts |
| `openpyxl` / `xlsxwriter` | Excel report generation |

## 🌐 Live Demo

Deployed on **Streamlit Community Cloud** — [Click here to try it](https://your-app.streamlit.app)

## 📁 Project Structure

```
crif_analayiser/
├── app.py              # Main Streamlit application
├── parser.py           # CRIF PDF parser (CrifParser class)
├── excel_generator.py  # Excel report generator
├── ai_analyzer.py      # Optional AI analysis module (Gemini / OpenAI)
├── requirements.txt    # Python dependencies
└── .streamlit/
    └── config.toml     # Streamlit theme & server config
```

## 📄 Usage

1. Open the app in your browser
2. Upload a **text-based, unencrypted** CRIF High Mark PDF
3. Explore the dashboard tabs:
   - 📊 **Executive Summary** — Score, KPIs, personal info
   - 🏦 **Accounts & Details** — Full trade line table
   - 🔍 **Inquiries** — Inquiry history
   - 📈 **Charts** — Visual analytics
   - 📄 **JSON Data** — Raw extracted data
4. Download the Excel report

## ⚠️ Notes

- Only **text-based PDFs** are supported (not scanned/image PDFs)
- No data is stored or transmitted — all processing happens locally in your browser session
- PDF files are **not committed** to this repository

## 📜 License

MIT License — feel free to use and modify.
