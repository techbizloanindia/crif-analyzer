"""
ai_analyzer.py — Deep AI analysis of parsed CRIF credit report data.

Uses Google Gemini (google-generativeai) by default.
Falls back gracefully if no API key is configured.
"""

import json
import re
from typing import Dict, Any, Optional


def _build_prompt(parsed_data: dict) -> str:
    """Build a compact but comprehensive prompt from parsed credit report data."""

    personal = parsed_data.get("personal_info", {})
    score = parsed_data.get("credit_score")
    metrics = parsed_data.get("summary_metrics", {})
    accounts = parsed_data.get("accounts", [])
    inquiries = parsed_data.get("inquiries", [])
    derived = parsed_data.get("derived_attributes", {})
    income_band = parsed_data.get("income_band", "-")

    # Summarize accounts compactly
    acct_summary_lines = []
    for i, a in enumerate(accounts[:25]):  # limit to 25 to keep prompt size reasonable
        acct_summary_lines.append(
            f"  [{i+1}] Lender={a.get('Lender','-')} | Type={a.get('Account Type','-')} | "
            f"Status={a.get('Status','-')} | Balance={a.get('Current Balance','-')} | "
            f"Overdue={a.get('Overdue Amount','-')} | DPD={a.get('DPD History / Payment History','-')} | "
            f"Opened={a.get('Date Opened','-')} | EMI={a.get('Installment Amount','-')} | "
            f"Asset Class={a.get('Asset Classification','-')}"
        )
    acct_block = "\n".join(acct_summary_lines) if acct_summary_lines else "  (No accounts detected)"

    inq_summary_lines = []
    for inq in inquiries[:15]:
        inq_summary_lines.append(
            f"  {inq.get('Inquiry Date','-')} | {inq.get('Inquirer','-')} | {inq.get('Purpose','-')} | Amt={inq.get('Amount','-')}"
        )
    inq_block = "\n".join(inq_summary_lines) if inq_summary_lines else "  (No inquiries detected)"

    prompt = f"""You are an expert credit analyst. Analyze the following CRIF High Mark credit bureau report data and provide a comprehensive, structured analysis in JSON format.

=== CREDIT REPORT DATA ===

PERSONAL:
  Name: {personal.get('Name', 'N/A')}
  PAN: {personal.get('PAN', 'N/A')}
  DOB: {personal.get('DOB', 'N/A')}
  Gender: {personal.get('Gender', 'N/A')}
  Mobile: {personal.get('Mobile', 'N/A')}

SCORE: {score if score else 'Not Available'}
INCOME BAND: {income_band}

SUMMARY METRICS:
  Total Accounts: {metrics.get('total_accounts', 0)}
  Active: {metrics.get('active_accounts', 0)}
  Closed: {metrics.get('closed_accounts', 0)}
  Overdue: {metrics.get('overdue_accounts', 0)}
  Secured: {metrics.get('secured_accounts', 0)}
  Unsecured: {metrics.get('unsecured_accounts', 0)}
  Total Outstanding: {metrics.get('total_outstanding', 'N/A')}
  Total Overdue: {metrics.get('total_overdue', 'N/A')}
  Sanctioned Amount: {metrics.get('sanctioned_amount', 'N/A')}

DERIVED ATTRIBUTES:
  Average Account Age: {derived.get('avg_age', '-')}
  Credit History Length: {derived.get('credit_history_length', '-')}
  Written-off Accounts: {derived.get('written_off_accounts', 0)}
  Settled Accounts: {derived.get('settled_accounts', 0)}
  Inquiries in Last 6 Months: {derived.get('inquiries_6m', 0)}
  New Accounts in Last 6 Months: {derived.get('new_accounts_6m', 0)}

ACCOUNTS ({len(accounts)} total):
{acct_block}

RECENT INQUIRIES ({len(inquiries)} total):
{inq_block}

=== REQUIRED OUTPUT ===

Return ONLY a valid JSON object with exactly these keys:

{{
  "executive_summary": "<3-5 sentence overall credit health summary — be specific with numbers from the data>",
  
  "overall_credit_health": "<EXCELLENT|GOOD|FAIR|POOR|VERY POOR>",
  
  "key_insights": [
    "<specific insight 1 with data>",
    "<specific insight 2 with data>",
    "<specific insight 3 with data>",
    "<specific insight 4 with data>",
    "<specific insight 5 with data>"
  ],
  
  "important_findings": {{
    "positive": [
      "<positive finding 1>",
      "<positive finding 2>"
    ],
    "negative": [
      "<negative finding 1>",
      "<negative finding 2>"
    ],
    "neutral": [
      "<observation 1>"
    ]
  }},
  
  "risk_analysis": {{
    "overall_risk_level": "<LOW|MEDIUM|HIGH|VERY HIGH>",
    "overall_risk_score": <0-100 where 0=no risk, 100=maximum risk>,
    "categories": {{
      "payment_behavior": {{
        "score": <0-100>,
        "level": "<LOW|MEDIUM|HIGH|VERY HIGH>",
        "explanation": "<1-2 sentences>"
      }},
      "credit_utilization": {{
        "score": <0-100>,
        "level": "<LOW|MEDIUM|HIGH|VERY HIGH>",
        "explanation": "<1-2 sentences>"
      }},
      "credit_age": {{
        "score": <0-100>,
        "level": "<LOW|MEDIUM|HIGH|VERY HIGH>",
        "explanation": "<1-2 sentences>"
      }},
      "inquiry_pressure": {{
        "score": <0-100>,
        "level": "<LOW|MEDIUM|HIGH|VERY HIGH>",
        "explanation": "<1-2 sentences>"
      }},
      "derogatory_marks": {{
        "score": <0-100>,
        "level": "<LOW|MEDIUM|HIGH|VERY HIGH>",
        "explanation": "<1-2 sentences>"
      }},
      "credit_mix": {{
        "score": <0-100>,
        "level": "<LOW|MEDIUM|HIGH|VERY HIGH>",
        "explanation": "<1-2 sentences>"
      }}
    }}
  }},
  
  "missing_information": [
    "<field or section that could not be extracted or is missing from the report>"
  ],
  
  "recommendations": [
    {{
      "priority": "<HIGH|MEDIUM|LOW>",
      "title": "<short action title>",
      "detail": "<specific actionable recommendation with numbers if possible>"
    }}
  ],
  
  "lender_analysis": [
    {{
      "lender": "<lender name>",
      "observation": "<1 sentence specific observation about this account>"
    }}
  ],
  
  "score_improvement_tips": [
    "<specific, numbered tip to improve or maintain credit score>"
  ]
}}

Be specific, data-driven, and reference actual numbers from the report. Do not use generic advice. Output ONLY the JSON with no markdown code fences."""

    return prompt


def _parse_ai_response(raw_text: str) -> dict:
    """Parse and clean the raw AI text response into a Python dict."""
    # Strip markdown code fences if present
    raw_text = raw_text.strip()
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
    raw_text = re.sub(r"```\s*$", "", raw_text, flags=re.MULTILINE)
    raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        # Try to extract JSON object from within the text
        m = re.search(r"\{[\s\S]+\}", raw_text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return {}


def analyze_with_gemini(parsed_data: dict, api_key: str, model_name: str = "gemini-1.5-flash") -> dict:
    """
    Send parsed credit report data to Gemini and return structured analysis.
    
    Returns a dict with keys: executive_summary, key_insights, important_findings,
    risk_analysis, missing_information, recommendations, lender_analysis,
    score_improvement_tips, overall_credit_health.
    """
    try:
        import google.generativeai as genai
    except ImportError:
        return {
            "_error": "google-generativeai package not installed. Run: pip install google-generativeai",
            "_error_type": "import_error"
        }

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        prompt = _build_prompt(parsed_data)

        generation_config = genai.types.GenerationConfig(
            temperature=0.3,
            max_output_tokens=4096,
        )

        response = model.generate_content(prompt, generation_config=generation_config)
        raw_text = response.text

        result = _parse_ai_response(raw_text)

        if not result:
            return {
                "_error": "AI returned an empty or unparseable response.",
                "_raw_response": raw_text[:2000],
                "_error_type": "parse_error"
            }

        result["_raw_response"] = raw_text
        result["_model"] = model_name
        result["_provider"] = "Google Gemini"
        return result

    except Exception as e:
        return {
            "_error": str(e),
            "_error_type": "api_error"
        }


def analyze_with_openai(parsed_data: dict, api_key: str, model_name: str = "gpt-4o") -> dict:
    """
    Send parsed credit report data to OpenAI and return structured analysis.
    """
    try:
        from openai import OpenAI
    except ImportError:
        return {
            "_error": "openai package not installed. Run: pip install openai",
            "_error_type": "import_error"
        }

    try:
        client = OpenAI(api_key=api_key)
        prompt = _build_prompt(parsed_data)

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an expert credit analyst. Return only valid JSON as instructed."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4096,
            temperature=0.3,
        )

        raw_text = response.choices[0].message.content
        result = _parse_ai_response(raw_text)

        if not result:
            return {
                "_error": "AI returned an empty or unparseable response.",
                "_raw_response": raw_text[:2000],
                "_error_type": "parse_error"
            }

        result["_raw_response"] = raw_text
        result["_model"] = model_name
        result["_provider"] = "OpenAI"
        return result

    except Exception as e:
        return {
            "_error": str(e),
            "_error_type": "api_error"
        }


def run_analysis(parsed_data: dict, provider: str, api_key: str) -> dict:
    """
    Main entry point. Dispatches to the correct AI provider.
    
    Args:
        parsed_data: Output dict from CrifParser.parse()
        provider: "gemini" or "openai"
        api_key: The API key string
    
    Returns:
        Structured analysis dict. Check for '_error' key on failure.
    """
    if not api_key or not api_key.strip():
        return {
            "_error": "No API key provided. Enter your Gemini or OpenAI API key in the sidebar.",
            "_error_type": "no_key"
        }

    if provider == "gemini":
        return analyze_with_gemini(parsed_data, api_key.strip())
    elif provider == "openai":
        return analyze_with_openai(parsed_data, api_key.strip())
    else:
        return {
            "_error": f"Unknown provider: '{provider}'. Choose 'gemini' or 'openai'.",
            "_error_type": "config_error"
        }


def get_risk_color(level: str) -> str:
    """Return a hex color string for a given risk level."""
    mapping = {
        "LOW": "#10b981",
        "MEDIUM": "#f39c12",
        "HIGH": "#ef4444",
        "VERY HIGH": "#7f1d1d",
    }
    return mapping.get(str(level).upper(), "#8c96a3")


def get_health_color(health: str) -> str:
    """Return a hex color for overall credit health rating."""
    mapping = {
        "EXCELLENT": "#10b981",
        "GOOD": "#2ecc71",
        "FAIR": "#f39c12",
        "POOR": "#ef4444",
        "VERY POOR": "#7f1d1d",
    }
    return mapping.get(str(health).upper(), "#8c96a3")


def get_priority_color(priority: str) -> str:
    mapping = {
        "HIGH": "#ef4444",
        "MEDIUM": "#f39c12",
        "LOW": "#10b981",
    }
    return mapping.get(str(priority).upper(), "#8c96a3")
