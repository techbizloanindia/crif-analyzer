import re
import pdfplumber
import pandas as pd
from typing import Dict, Any, List, Optional


class CrifParser:
    def __init__(self, file_path_or_bytes):
        self.file_path_or_bytes = file_path_or_bytes
        self.raw_text_by_page = {}
        self.tables_by_page = {}
        self.metadata = {}
        self.personal_info = {}
        self.loan_application = {}
        self.credit_score = None
        self.score_factors = None
        self.income_band = None
        self.summary_metrics = {}
        self.derived_attributes = {}
        self.accounts = []
        self.inquiries = []
        self.status_details = []

    def parse(self) -> Dict[str, Any]:
        """Runs the parsing process and returns a structured dictionary."""
        try:
            with pdfplumber.open(self.file_path_or_bytes) as pdf:
                for idx, page in enumerate(pdf.pages):
                    page_num = idx + 1
                    text = page.extract_text() or ""
                    self.raw_text_by_page[page_num] = text

                    tables = page.extract_tables()
                    self.tables_by_page[page_num] = []
                    for table in tables:
                        if table:
                            cleaned = [
                                row for row in table
                                if any(cell is not None and str(cell).strip() != "" for cell in row)
                            ]
                            if cleaned:
                                self.tables_by_page[page_num].append(cleaned)

            # Run all extraction routines
            self._extract_metadata_and_score()
            self._extract_personal_info()
            self._extract_loan_application()
            self._extract_summary_metrics()
            self._extract_derived_attributes()
            self._extract_structured_accounts()
            self._extract_structured_inquiries()
            self._extract_status_details()

            return {
                "metadata": self.metadata,
                "personal_info": self.personal_info,
                "loan_application": self.loan_application,
                "credit_score": self.credit_score,
                "score_factors": self.score_factors,
                "income_band": self.income_band,
                "summary_metrics": self.summary_metrics,
                "derived_attributes": self.derived_attributes,
                "accounts": self.accounts,
                "inquiries": self.inquiries,
                "status_details": self.status_details,
                "raw_text_by_page": self.raw_text_by_page,
                "tables_by_page": self.tables_by_page,
            }
        except Exception as e:
            raise Exception(
                f"Failed to parse PDF. Please verify that your file is a valid "
                f"unencrypted CRIF/CIBIL report PDF. Error: {str(e)}"
            )

    # ─── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _clean_val(val_str) -> float:
        cleaned = re.sub(r"[^\d\.]", "", str(val_str))
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0

    def _combined_text(self, start_page=1, end_page=None):
        if end_page is None:
            end_page = max(self.raw_text_by_page.keys()) if self.raw_text_by_page else 1
        pages = range(start_page, end_page + 1)
        return "\n".join(self.raw_text_by_page.get(p, "") for p in pages)

    @staticmethod
    def _first_match(text, patterns, group=1, flags=re.IGNORECASE) -> str:
        for pat in patterns:
            m = re.search(pat, text, flags)
            if m:
                return m.group(group).strip()
        return "N/A"

    # ─── Extraction Methods ──────────────────────────────────────────────────

    def _extract_metadata_and_score(self):
        combined = self._combined_text(1, min(3, len(self.raw_text_by_page)))

        # Report Reference / ID
        self.metadata["ref_number"] = self._first_match(combined, [
            r"Report\s*(?:Reference|Ref|ID)\s*(?:No|#)?\s*[:\-]?\s*([A-Za-z0-9\-]+)",
            r"CRIF\s*Ref\s*(?:No|#)?\s*[:\-]?\s*([A-Za-z0-9\-]+)",
            r"High\s*Mark\s*Ref\s*(?:No|#)?\s*[:\-]?\s*([A-Za-z0-9\-]+)",
            r"CHM\s*Ref\s*(?:No|#)?\s*[:\-]?\s*([A-Za-z0-9\-]+)",
        ])

        # Report Date
        self.metadata["report_date"] = self._first_match(combined, [
            r"Report\s*Date\s*[:\-]?\s*(\d{2}[-\/\s][A-Za-z0-9]{2,3}[-\/\s]\d{2,4})",
            r"Date\s*of\s*Issue\s*[:\-]?\s*(\d{2}[-\/\s][A-Za-z0-9]{2,3}[-\/\s]\d{2,4})",
            r"Date\s*[:\-]?\s*(\d{2}[-\/]\d{2}[-\/]\d{4})",
        ])

        # Prepared For
        self.metadata["prepared_for"] = self._first_match(combined, [
            r"Prepared\s*For\s*[:\-]?\s*([A-Za-z0-9\s\.\,\-\&\/]+?)(?=\s{2,}|\n|Report|Date)",
        ])

        # Credit Score
        for pat in [
            r"Score\s*Value\s*[:\-]?\s*(\d{3})",
            r"CRIF\s*High\s*Mark\s*Score\s*[:\-]?\s*(\d{3})",
            r"CRIF\s*Score\s*[:\-]?\s*(\d{3})",
            r"Credit\s*Score\s*[:\-]?\s*(\d{3})",
            r"PERFORM[A-Z\s\.]*Score\s*[:\-]?\s*(\d{3})",
            r"CIBIL\s*Score\s*[:\-]?\s*(\d{3})",
        ]:
            m = re.search(pat, combined, re.IGNORECASE)
            if m:
                s = int(m.group(1))
                if 300 <= s <= 900:
                    self.credit_score = s
                    break

        # Fallback score from any 3-digit number near score keyword
        if not self.credit_score:
            for line in combined.split("\n"):
                if any(kw in line.lower() for kw in ["score", "highmark", "crif", "cibil"]):
                    for num in re.findall(r"\b(\d{3})\b", line):
                        s = int(num)
                        if 300 <= s <= 900:
                            self.credit_score = s
                            break
                if self.credit_score:
                    break

        # Score Factors
        self.score_factors = self._first_match(combined, [
            r"Score\s*Factors?\s*[:\-]?\s*([A-Za-z0-9\|\s\,]+?)(?=\n|Income|$)",
        ])
        if self.score_factors == "N/A":
            self.score_factors = "-"

        # Income Band
        self.income_band = self._first_match(combined, [
            r"Income\s*Band\s*(?:\(Annual\))?\s*[:\-]?\s*([\d\,\s\-\+]+(?:Lakh|Lac|INR)?)",
            r"Annual\s*Income\s*[:\-]?\s*([\d\,\s\-]+)",
        ])
        if self.income_band == "N/A":
            self.income_band = "-"

    def _extract_personal_info(self):
        combined = self._combined_text(1, min(4, len(self.raw_text_by_page)))

        # PAN
        pan_m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b", combined)
        self.personal_info["PAN"] = pan_m.group(1) if pan_m else "N/A"

        # DOB
        self.personal_info["DOB"] = self._first_match(combined, [
            r"DOB(?:/Age)?\s*[:\-]?\s*(\d{2}[-\/\s]\d{2}[-\/\s]\d{4})",
            r"Date\s*of\s*Birth\s*[:\-]?\s*(\d{2}[-\/\s]\d{2}[-\/\s]\d{4})",
            r"DOB\s*[:\-]?\s*(\d{2}[-\/\s]\d{2}[-\/\s]\d{4})",
            r"DOB\s*[:\-]?\s*(\d{2}[-\/\s][A-Za-z0-9]{2,3}[-\/\s]\d{2,4})",
            r"Date\s*of\s*Birth\s*[:\-]?\s*(\d{2}[-\/\s][A-Za-z0-9]{2,3}[-\/\s]\d{2,4})",
        ])

        # Full Name
        name = self._first_match(combined, [
            r"\bName\s*:\s*([A-Za-z\s\.\,\-]+?)(?=\s*DOB|\s*DOB/Age|\s*Gender|\s{2,}|\n|$)",
            r"Borrower\s*Name\s*[:\-]?\s*([A-Za-z\s\.\,\-]+?)(?=\s{2,}|\bCRIF\b|\bScore\b|\bPAN\b|\bRating\b|$)",
            r"(?:Full\s*)?Name\s*[:\-]?\s*([A-Za-z\s\.\,\-]+?)(?=\s{2,}|\bCRIF\b|\bScore\b|\bPAN\b|\bRating\b|$)",
        ])
        if name == "N/A" or len(name) < 3 or "report" in name.lower() or "crif" in name.lower():
            lines = [l.strip() for l in combined.split("\n") if l.strip()]
            for line in lines[:15]:
                if (
                    "report" not in line.lower()
                    and "crif" not in line.lower()
                    and "high mark" not in line.lower()
                    and re.match(r"^[A-Z\s\.]+$", line)
                    and 4 < len(line) < 50
                ):
                    name = line
                    break
        self.personal_info["Name"] = name if name != "N/A" else "N/A"

        # Father's Name
        self.personal_info["Father"] = self._first_match(combined, [
            r"Father\s*:\s*([A-Za-z0-9\s\.\,\-\/]+?)(?=\s*Spouse|\s*Mother|\s{2,}|\n|$)",
            r"Father'?s?\s*Name\s*[:\-]?\s*([A-Za-z0-9\s\.\,\-\/]+?)(?=\s{2,}|\bScore\b|\bRating\b|\bPAN\b|\bDOB\b|\n|$)",
        ])

        # Aadhaar
        aad_m = re.search(r"([0-9Xx\s\*]{12,19})\s*\[UID\]", combined, re.IGNORECASE)
        if not aad_m:
            aad_m = re.search(r"([0-9Xx\s\*]{12,19})\s*\[Aadhaar\]", combined, re.IGNORECASE)
        if not aad_m:
            aad_m = re.search(r"(?:Aadhaar|UID)\s*(?:\(masked\))?\s*[:\-]?\s*([0-9Xx\s\*]{12,19})", combined, re.IGNORECASE)
        self.personal_info["Aadhaar"] = aad_m.group(1).strip() if aad_m else "N/A"

        # Address
        addr_m = re.search(
            r"Current\s*Address\s*[:\-]?\s*([A-Za-z0-9\s\.\,\-\#\/\:\(\)\n]+?)(?=\s{2,}|\bOther\s*Address\b|\bCredit\s*Portfolio\b|\bDetailed\s*Credit\b|\bLender\s*Inquiries\b|$)",
            combined, re.IGNORECASE
        )
        if not addr_m:
            addr_m = re.search(
                r"Address\s*[:\-]?\s*([A-Za-z0-9\s\.\,\-\#\/\:\(\)\n]+?)(?=\s{2,}|\bCredit\s*Portfolio\b|\bDetailed\s*Credit\b|\bLender\s*Inquiries\b|$)",
                combined, re.IGNORECASE
            )
        self.personal_info["Address"] = (
            addr_m.group(1).replace("\n", " ").strip() if addr_m else "N/A"
        )

        # Email
        email_m = re.search(r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b", combined)
        self.personal_info["Email"] = email_m.group(1) if email_m else "N/A"

        # Mobile
        self.personal_info["Mobile"] = self._first_match(combined, [
            r"Phone\s*Numbers?\s*[:\-]?\s*([0-9Xx\*]{10,12})",
            r"Mobile\s*(?:No|Number)?\s*[:\-]?\s*([0-9Xx\*]{10,12})",
            r"Phone\s*(?:No|Number)?\s*[:\-]?\s*([0-9Xx\*]{10,12})",
            r"Telephone\s*[:\-]?\s*([0-9Xx\*]{10,12})",
        ])

        # Gender
        gender_m = re.search(r"\b(Male|Female|Transgender|MALE|FEMALE)\b", combined)
        self.personal_info["Gender"] = gender_m.group(1).capitalize() if gender_m else "N/A"

    def _extract_loan_application(self):
        combined = self._combined_text(1, min(3, len(self.raw_text_by_page)))

        self.loan_application["loan_amount"] = self._first_match(combined, [
            r"Loan\s*Amount\s*(?:Applied)?\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.]+)",
        ])
        self.loan_application["application_id"] = self._first_match(combined, [
            r"(?:Application\s*ID|App\s*ID|LOS\s*App\s*ID)\s*[:\-]?\s*([A-Za-z0-9]+)",
        ])
        self.loan_application["inquiry_purpose"] = self._first_match(combined, [
            r"(?:Inquiry|Enquiry)\s*Purpose\s*[:\-]?\s*([A-Za-z0-9\-]+)",
        ])
        self.loan_application["inquiry_stage"] = self._first_match(combined, [
            r"(?:Inquiry|Enquiry)\s*Stage\s*[:\-]?\s*([A-Za-z0-9\-]+)",
        ])
        self.loan_application["request_datetime"] = self._first_match(combined, [
            r"Request\s*Date(?:/Time)?\s*[:\-]?\s*(\d{2}[-\/]\d{2}[-\/]\d{4}[\s\d:]*)",
        ])
        self.loan_application["branch"] = self._first_match(combined, [
            r"Branch\s*[:\-]?\s*([A-Za-z0-9\s]+?)(?=\n|$)",
        ])

    def _extract_summary_metrics(self):
        combined = self._combined_text()

        metrics = {
            "total_accounts": 0,
            "active_accounts": 0,
            "closed_accounts": 0,
            "overdue_accounts": 0,
            "secured_accounts": 0,
            "unsecured_accounts": 0,
            "total_outstanding": "N/A",
            "total_overdue": "N/A",
            "sanctioned_amount": "N/A",
            "disbursed_amount": "N/A",
        }

        def pick(patterns):
            return self._first_match(combined, patterns)

        # Account counts
        ta = pick([r"(?:Total|No\s*of)\s*Accounts\s*(?:Value|No)?\s*[:\-\s]*(\d+)"])
        if ta != "N/A":
            metrics["total_accounts"] = int(ta)

        aa = pick([r"Active\s*Accounts\s*(?:Value|No)?\s*[:\-\s]*(\d+)"])
        if aa != "N/A":
            metrics["active_accounts"] = int(aa)

        ca = pick([r"Closed\s*Accounts\s*(?:Value|No)?\s*[:\-\s]*(\d+)"])
        if ca != "N/A":
            metrics["closed_accounts"] = int(ca)

        oa = pick([r"(?:Overdue|Delinquent)\s*Accounts\s*(?:Value|No)?\s*[:\-\s]*(\d+)"])
        if oa != "N/A":
            metrics["overdue_accounts"] = int(oa)

        sec = pick([r"Secured\s*Accounts\s*(?:Value|No)?\s*[:\-\s]*(\d+)"])
        if sec != "N/A":
            metrics["secured_accounts"] = int(sec)

        unsec = pick([r"Unsecured\s*Accounts\s*(?:Value|No)?\s*[:\-\s]*(\d+)"])
        if unsec != "N/A":
            metrics["unsecured_accounts"] = int(unsec)

        # Amounts (preserve as strings like the reference, requiring at least one digit)
        out_m = re.search(
            r"(?:Current\s*Balance|Total\s*Outstanding(?:\s*Balance)?)\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.]+)",
            combined, re.IGNORECASE
        )
        if out_m and any(c.isdigit() for c in out_m.group(1)):
            metrics["total_outstanding"] = out_m.group(1).strip()

        od_m = re.search(
            r"Total\s*Overdue\s*(?:Balance|Amount)?\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.]+)",
            combined, re.IGNORECASE
        )
        if od_m and any(c.isdigit() for c in od_m.group(1)):
            metrics["total_overdue"] = od_m.group(1).strip()

        sanc_m = re.search(
            r"(?:Sanctioned|Sanction)\s*Amount\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.]+)",
            combined, re.IGNORECASE
        )
        if sanc_m and any(c.isdigit() for c in sanc_m.group(1)):
            metrics["sanctioned_amount"] = sanc_m.group(1).strip()

        disb_m = re.search(
            r"Disbursed?\s*Amount\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.]+)",
            combined, re.IGNORECASE
        )
        if disb_m and any(c.isdigit() for c in disb_m.group(1)):
            metrics["disbursed_amount"] = disb_m.group(1).strip()

        # Fall back: inspect summary tables
        for page_num, tables in self.tables_by_page.items():
            for table in tables:
                flat_cells = [str(c).lower() for row in table for c in row if c]
                if "active" in flat_cells and any("total" in c for c in flat_cells):
                    for row in table:
                        row_str = " ".join(str(c) for c in row if c).lower()
                        digits = re.findall(r"\b\d+\b", row_str)
                        if "total" in row_str and "account" in row_str and digits:
                            metrics["total_accounts"] = int(digits[0])
                        elif "active" in row_str and "account" in row_str and digits:
                            metrics["active_accounts"] = int(digits[0])
                        elif "closed" in row_str and "account" in row_str and digits:
                            metrics["closed_accounts"] = int(digits[0])

        self.summary_metrics = metrics

    def _extract_derived_attributes(self):
        combined = self._combined_text()

        da = {
            "avg_age": "-",
            "credit_history_length": "-",
            "written_off_accounts": 0,
            "written_off_amount": "-",
            "settled_accounts": 0,
            "restructured_accounts": 0,
            "inquiries_6m": 0,
            "new_accounts_6m": 0,
            "new_delinq_6m": 0,
        }

        woa = self._first_match(combined, [
            r"(?:Total\s*)?Written.?off\s*Accounts?\s*[:\-]?\s*(\d+)",
        ])
        if woa != "N/A":
            da["written_off_accounts"] = int(woa)

        wo_amt = self._first_match(combined, [
            r"(?:Total\s*)?Written.?off\s*Amount\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.]+)",
        ])
        if wo_amt != "N/A":
            da["written_off_amount"] = wo_amt

        settled = self._first_match(combined, [
            r"Settled\s*Accounts?\s*[:\-]?\s*(\d+)",
        ])
        if settled != "N/A":
            da["settled_accounts"] = int(settled)

        restr = self._first_match(combined, [
            r"Restructured\s*Accounts?\s*[:\-]?\s*(\d+)",
        ])
        if restr != "N/A":
            da["restructured_accounts"] = int(restr)

        inq6m = self._first_match(combined, [
            r"Inquiries\s*in\s*Last\s*6?\s*(?:Six)?\s*Months?\s*[:\-]?\s*(\d+)",
        ])
        if inq6m != "N/A":
            da["inquiries_6m"] = int(inq6m)

        na6m = self._first_match(combined, [
            r"New\s*Accounts?\s*in\s*Last\s*6?\s*(?:Six)?\s*Months?\s*[:\-]?\s*(\d+)",
        ])
        if na6m != "N/A":
            da["new_accounts_6m"] = int(na6m)

        nd6m = self._first_match(combined, [
            r"New\s*Delinquent\s*Accounts?\s*(?:in\s*Last\s*6?\s*(?:Six)?\s*Months?)?\s*[:\-]?\s*(\d+)",
        ])
        if nd6m != "N/A":
            da["new_delinq_6m"] = int(nd6m)

        # Avg age from text like "3 yrs 5 months" or "Average Account Age: 3 5"
        age_m = re.search(
            r"Average\s*Account\s*Age\s*[:\-]?\s*(\d+)\s*(?:yr(?:s)?|year(?:s)?)\s*(\d+)\s*month(?:s)?",
            combined, re.IGNORECASE
        )
        if age_m:
            da["avg_age"] = f"{age_m.group(1)} yrs {age_m.group(2)} months"
        else:
            age2_m = re.search(
                r"Average\s*Account\s*Age\s*[:\-]?\s*(\d+)\s+(\d+)",
                combined, re.IGNORECASE
            )
            if age2_m:
                da["avg_age"] = f"{age2_m.group(1)} yrs {age2_m.group(2)} months"

        hist_m = re.search(
            r"Length\s*of\s*Credit\s*History\s*[:\-]?\s*(\d+)\s*(?:yr(?:s)?|year(?:s)?)\s*(\d+)\s*month(?:s)?",
            combined, re.IGNORECASE
        )
        if hist_m:
            da["credit_history_length"] = f"{hist_m.group(1)} yrs {hist_m.group(2)} months"

        self.derived_attributes = da

    def _parse_crif_text_blocks(self, text_clean) -> list:
        blocks = re.split(r"(?=\b\d+\s+Account\s+Type\s*:)", text_clean)
        accounts = []

        def extract_date_field(block, label):
            lines = block.split("\n")
            for i, line in enumerate(lines):
                if label.lower() in line.lower():
                    match_same = re.search(re.escape(label) + r"\s*(\d{2}-\d{2}-\d{4})", line, re.IGNORECASE)
                    if match_same:
                        return match_same.group(1)
                    if i > 0:
                        above_line = lines[i-1].strip()
                        match_above = re.search(r"\b(\d{2}-\d{2}-\d{4})\b", above_line)
                        if match_above:
                            return match_above.group(1)
            return "-"

        for block in blocks[1:]:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if not lines:
                continue
            
            first_line = lines[0]
            match_head = re.search(r"\b(\d+)\s+Account\s+Type\s*:\s*(.+?)\s+Credit\s+Grantor\s*:\s*(.+?)\s+Account\s*#\s*:\s*(.+?)\s+Info\.\s+as\s+of\s*:\s*(\d{2}-\d{2}-\d{4})", first_line, re.IGNORECASE)
            if not match_head:
                match_head = re.search(r"\b(\d+)\s+Account\s+Type\s*:\s*(.+?)\s+Credit\s+Grantor\s*:\s*(.+)", first_line, re.IGNORECASE)
                if not match_head:
                    continue
                    
            idx = match_head.group(1)
            acct_type = match_head.group(2).strip()
            lender = match_head.group(3).strip()
            
            acct_no = "-"
            info_as_of = "-"
            if len(match_head.groups()) >= 5:
                acct_no = match_head.group(4).strip()
                info_as_of = match_head.group(5).strip()
            
            disb_date = extract_date_field(block, "Disbursed Date:")
            last_payment_date = extract_date_field(block, "Last Payment Date:")
            closed_date = extract_date_field(block, "Closed Date:")
            
            def rx(pattern, default="-"):
                m = re.search(pattern, block, re.IGNORECASE)
                return m.group(1).strip() if m else default

            ownership = rx(r"Ownership\s*:\s*(.+?)(?=\s+Disbursed|\n|$)")
            disb_amt = rx(r"Disbd\s+Amt/High\s+Credit\s*:\s*([0-9\,\.\-]+)")
            credit_limit = rx(r"Credit\s+Limit\s*:\s*([0-9\,\.\-]+)")
            current_balance = rx(r"Current\s+Balance\s*:\s*([0-9\,\.\-]+)")
            overdue_amt = rx(r"Overdue\s+Amt\s*:\s*([0-9\,\.\-]+)")
            installment_amt = rx(r"InstlAmt/Freq\s*:\s*(.+?)(?=\s+Tenure|\n|$)")
            
            # DPD and Asset class
            asset_class = rx(r"Payment\s+History/Asset\s+Classification:\s*\n\s*([A-Za-z0-9\s/]+)", "-")
            dpd_history = rx(r"Payment\s+History/Asset\s+Classification:\s*\n\s*([^\n]+)", "-")
            interest_rate = rx(r"Interest\s+Rate\s*:\s*([0-9\.\%\s\-]+)")
            occupation = rx(r"Occupation\s*:\s*(.+?)(?=\s+Payment|\n|$)")
            
            # Security Details
            security_val = "-"
            sec_type_match = re.search(r"Collateral/Security\s+Details:\s*\n\s*([^\n]+)\s*\n\s*([^\n]+)", block, re.IGNORECASE)
            if sec_type_match:
                sec_header = sec_type_match.group(1)
                sec_vals = sec_type_match.group(2)
                security_val = f"{sec_header.strip()} : {sec_vals.strip()}"
            else:
                sec_simple = re.search(r"Security\s+Type\s+Type\s+of\s+Charge\s+Security\s+Value\s+Date\s+Of\s+Value\s*\n\s*([^\n]+)", block, re.IGNORECASE)
                if sec_simple:
                    security_val = sec_simple.group(1).strip()

            # Status logic
            status = "Active"
            if closed_date != "-":
                status = "Closed"
            elif "CLOSED" in block:
                status = "Closed"
            elif "SETTLED" in block:
                status = "Settled"
            elif "WRITTEN OFF" in block or "WRITE-OFF" in block:
                status = "Written Off"
            elif "ACTIVE" in block:
                status = "Active"

            accounts.append({
                "Lender": lender,
                "Account Number": acct_no,
                "Account Type": acct_type,
                "Status": status,
                "Security": security_val,
                "Date Opened": disb_date,
                "Last Reported": info_as_of,
                "Credit Limit/Sanctioned": credit_limit,
                "Current Balance": current_balance,
                "Overdue Amount": overdue_amt,
                "Write-off Amount": rx(r"Total\s+Writeoff\s+Amt\s*:\s*([0-9\,\.\-]+)", "0"),
                "WO/Settled Status": rx(r"Settlement\s+Amt\s*:\s*([0-9\,\.\-]+)", "-"),
                "Last Payment": last_payment_date,
                "Ownership": ownership,
                "Occupation": occupation,
                "High Credit": disb_amt,
                "Asset Classification": asset_class,
                "Interest Rate": interest_rate,
                "Installment Amount": installment_amt,
                "DPD History / Payment History": dpd_history,
            })
        return accounts

    def _extract_structured_accounts(self):
        """
        Extract loan/account records matching the reference Excel columns.
        """
        combined = self._combined_text()
        
        # Check if the PDF has text-block style accounts (real CRIF reports)
        if re.search(r"\b\d+\s+Account\s+Type\s*:", combined):
            # Clean split words
            text_clean = re.sub(r"C\s*L\s*\n\s*O\s*S\s*E\s*D", "CLOSED", combined, flags=re.IGNORECASE)
            text_clean = re.sub(r"A\s*C\s*\n\s*T\s*I\s*V\s*E", "ACTIVE", text_clean, flags=re.IGNORECASE)
            text_clean = re.sub(r"S\s*E\s*T\s*T\s*\n\s*L\s*E\s*D", "SETTLED", text_clean, flags=re.IGNORECASE)
            text_clean = re.sub(r"W\s*R\s*I\s*T\s*T\s*E\s*N\s*-\s*O\s*F\s*F", "WRITTEN OFF", text_clean, flags=re.IGNORECASE)
            
            # Reconstruct split dates
            text_clean = re.sub(r"\b(\d{2}-\d{2}-)\s*\n\s*([^\n]+)\s*\n\s*(\d{4})\b", r"\1\3\n\2", text_clean)
            
            account_list = self._parse_crif_text_blocks(text_clean)
        else:
            account_list = []
            last_header_map = None
            last_col_count = None

            # Column keyword mappings for reference-style columns
            HEADER_KEYWORDS = {
                "acct_type":     ["acct type", "account type", "type of account", "loan type", "product"],
                "status":        ["status", "account status", "acct status"],
                "security":      ["security", "secured", "collateral"],
                "disbursed_date":["disbursed date", "date disbursed", "date opened", "open date", "disbursal"],
                "last_reported": ["last reported", "date reported", "last updated", "reporting date"],
                "disbursed_amt": ["disbursed amt", "disbursed amount", "sanctioned amount", "sanctioned amt", "credit limit", "limit"],
                "current_bal":   ["current bal", "current balance", "outstanding", "outstanding balance"],
                "overdue_amt":   ["overdue amt", "overdue amount", "overdue"],
                "write_off_amt": ["write-off amt", "write off amt", "written off", "writeoff"],
                "wo_status":     ["wo/settled", "written-off_settled", "wo settled", "settlement status", "wo status"],
                "last_payment":  ["last payment", "last payment date", "payment date"],
                "ownership":     ["ownership", "ownership ind", "owner"],
                "occupation":    ["occupation", "employment"],
                "lender":        ["lender", "member name", "creditor", "bank name", "institution"],
                "account_no":    ["account no", "account number", "acct no", "acct #", "account #"],
                "high_credit":   ["high credit", "high balance", "highest balance"],
                "interest_rate": ["interest rate", "rate of interest", "roi"],
                "installment":   ["installment", "emi", "monthly payment"],
                "dpd_history":   ["dpd", "days past due", "payment history", "dpd history"],
                "asset_class":   ["asset classification", "asset class", "npa classification", "asset quality", "classification", "sub-standard", "standard"],
            }

            def map_header(h_str: str) -> Optional[str]:
                h_lower = h_str.strip().lower().replace("\n", " ")
                for field, kws in HEADER_KEYWORDS.items():
                    for kw in kws:
                        if kw in h_lower:
                            return field
                return None

            ACCOUNT_TRIGGER_KW = [
                "account type", "acct type", "current bal", "current balance",
                "outstanding", "overdue", "disbursed date", "disbursed amt",
                "last reported", "security", "ownership", "occupation",
                "lender", "member name", "date opened"
            ]
            INQ_KW = ["inquiry date", "inquirer", "purpose", "inquiry amount"]

            for page_num, tables in sorted(self.tables_by_page.items()):
                for table in tables:
                    if not table:
                        continue
                    first_row = [str(c).strip().lower().replace("\n", " ") for c in table[0] if c]
                    is_acct_table = False

                    trigger_count = sum(1 for kw in ACCOUNT_TRIGGER_KW if any(kw in h for h in first_row))
                    inq_count = sum(1 for kw in INQ_KW if any(kw in h for h in first_row))

                    if trigger_count >= 2 and inq_count < 2:
                        is_acct_table = True
                        header_map = {}
                        for idx, cell in enumerate(table[0]):
                            if cell:
                                field = map_header(str(cell))
                                if field and field not in header_map:
                                    header_map[field] = idx
                        last_header_map = header_map
                        last_col_count = len(table[0])
                        start_row_idx = 1
                    else:
                        if last_header_map and len(table[0]) == last_col_count and inq_count < 2:
                            is_acct_table = True
                            header_map = last_header_map
                            start_row_idx = 0

                    if is_acct_table:
                        for row in table[start_row_idx:]:
                            if not row or len(row) <= max(header_map.values(), default=0):
                                continue

                            def g(key, default="-"):
                                if key in header_map:
                                    c = row[header_map[key]]
                                    return str(c).strip() if c is not None else default
                                return default

                            acct_type = g("acct_type", g("lender", "Unknown"))
                            if acct_type in ("Unknown", "", "-", "N/A", "None"):
                                continue

                            wo_status = g("wo_status", "")
                            if any(kw in acct_type.lower() for kw in ["type", "account", "lender", "status"]):
                                if any(kw in acct_type.lower() for kw in ["account type", "acct type"]):
                                    continue

                            account_list.append({
                                "Lender": g("lender", "-"),
                                "Account Number": g("account_no", "-"),
                                "Account Type": acct_type,
                                "Status": g("status", "-"),
                                "Security": g("security", "-"),
                                "Date Opened": g("disbursed_date", "-"),
                                "Last Reported": g("last_reported", "-"),
                                "Credit Limit/Sanctioned": g("disbursed_amt", "0"),
                                "Current Balance": g("current_bal", "0"),
                                "Overdue Amount": g("overdue_amt", "0"),
                                "Write-off Amount": g("write_off_amt", "0"),
                                "WO/Settled Status": wo_status,
                                "Last Payment": g("last_payment", "-"),
                                "Ownership": g("ownership", "-"),
                                "Occupation": g("occupation", "-"),
                                "High Credit": g("high_credit", "-"),
                                "Asset Classification": g("asset_class", "-"),
                                "Interest Rate": g("interest_rate", "-"),
                                "Installment Amount": g("installment", "-"),
                                "DPD History / Payment History": g("dpd_history", "-"),
                            })

            if not account_list:
                account_list = self._fallback_account_parse()

        # Post-process: fill account counts from actual data if metrics were 0
        if self.summary_metrics.get("total_accounts", 0) == 0 and account_list:
            self.summary_metrics["total_accounts"] = len(account_list)
        if self.summary_metrics.get("active_accounts", 0) == 0 and account_list:
            self.summary_metrics["active_accounts"] = sum(
                1 for a in account_list if "active" in str(a.get("Status", "")).lower()
            )
        if self.summary_metrics.get("closed_accounts", 0) == 0 and account_list:
            self.summary_metrics["closed_accounts"] = sum(
                1 for a in account_list if "closed" in str(a.get("Status", "")).lower()
            )
        if self.summary_metrics.get("overdue_accounts", 0) == 0 and account_list:
            self.summary_metrics["overdue_accounts"] = sum(
                1 for a in account_list
                if self._clean_val(a.get("Overdue Amount", a.get("Overdue Amt", "0"))) > 0
            )
        
        secured_keywords = ["home", "housing", "property", "auto", "vehicle", "car", "gold", "two wheeler", "motorcycle", "secured"]
        
        if self.summary_metrics.get("secured_accounts", 0) == 0 and account_list:
            self.summary_metrics["secured_accounts"] = sum(
                1 for a in account_list
                if any(re.search(rf"\b{re.escape(kw)}\b", str(a.get("Account Type", "")).lower()) for kw in secured_keywords)
                or ("secured" in str(a.get("Security", "")).lower() and "un-secured" not in str(a.get("Security", "")).lower())
            )
        if self.summary_metrics.get("unsecured_accounts", 0) == 0 and account_list:
            self.summary_metrics["unsecured_accounts"] = sum(
                1 for a in account_list
                if not (
                    any(re.search(rf"\b{re.escape(kw)}\b", str(a.get("Account Type", "")).lower()) for kw in secured_keywords)
                    or ("secured" in str(a.get("Security", "")).lower() and "un-secured" not in str(a.get("Security", "")).lower())
                )
            )

        # Recalculate summary metrics if they are default N/A or 0
        if (self.summary_metrics.get("sanctioned_amount") == "N/A" or not self.summary_metrics.get("sanctioned_amount")) and account_list:
            total_limit = sum(self._clean_val(a.get("Credit Limit/Sanctioned", 0)) for a in account_list)
            self.summary_metrics["sanctioned_amount"] = f"{total_limit:,.2f}" if total_limit > 0 else "0.00"
            
        if (self.summary_metrics.get("disbursed_amount") == "N/A" or not self.summary_metrics.get("disbursed_amount")) and account_list:
            total_disbursed = sum(
                self._clean_val(a.get("High Credit", 0)) if self._clean_val(a.get("High Credit", 0)) > 0 
                else self._clean_val(a.get("Credit Limit/Sanctioned", 0)) 
                for a in account_list
            )
            self.summary_metrics["disbursed_amount"] = f"{total_disbursed:,.2f}" if total_disbursed > 0 else "0.00"

        # Calculate/fill derived attributes
        report_date_str = self.metadata.get("report_date")
        from datetime import datetime
        
        def parse_date_local(d_str):
            if not d_str or str(d_str).strip() in ["-", "N/A", "N/A / N/A"]:
                return None
            for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d-%b-%Y", "%d-%m-%y", "%d/%m/%y", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(str(d_str).strip(), fmt)
                except ValueError:
                    continue
            return None
            
        r_date = parse_date_local(report_date_str) or datetime.now()
        
        parsed_dates = []
        for acct in account_list:
            opened_dt = parse_date_local(acct.get("Date Opened"))
            if opened_dt:
                parsed_dates.append(opened_dt)
                
        if parsed_dates:
            ages = []
            new_accts = 0
            for d in parsed_dates:
                diff_m = (r_date.year - d.year) * 12 + (r_date.month - d.month)
                diff_m = max(0, diff_m)
                ages.append(diff_m)
                if diff_m <= 6:
                    new_accts += 1
            if ages:
                avg_m = sum(ages) / len(ages)
                self.derived_attributes["avg_age"] = f"{int(avg_m // 12)} yrs {int(avg_m % 12)} months"
                
                earliest = min(parsed_dates)
                hist_m = (r_date.year - earliest.year) * 12 + (r_date.month - earliest.month)
                hist_m = max(0, hist_m)
                self.derived_attributes["credit_history_length"] = f"{int(hist_m // 12)} yrs {int(hist_m % 12)} months"
            self.derived_attributes["new_accounts_6m"] = new_accts
            
        # Inquiries count last 6 months
        inq_6m = 0
        for inq in self.inquiries:
            inq_dt = parse_date_local(inq.get("Inquiry Date"))
            if inq_dt:
                diff_m = (r_date.year - inq_dt.year) * 12 + (r_date.month - inq_dt.month)
                if diff_m <= 6:
                    inq_6m += 1
        self.derived_attributes["inquiries_6m"] = inq_6m
        
        # Status counts
        self.derived_attributes["written_off_accounts"] = sum(1 for a in account_list if "write" in str(a.get("Status", "")).lower())
        self.derived_attributes["settled_accounts"] = sum(1 for a in account_list if "settled" in str(a.get("Status", "")).lower())
        self.derived_attributes["restructured_accounts"] = sum(1 for a in account_list if "restructured" in str(a.get("Status", "")).lower())
        
        # Total outstanding and overdue if N/A or 0
        if (self.summary_metrics.get("total_outstanding") == "N/A" or not self.summary_metrics.get("total_outstanding") or self.summary_metrics.get("total_outstanding") == "0.00") and account_list:
            total_outstanding_val = sum(self._clean_val(a.get("Current Balance", 0)) for a in account_list)
            self.summary_metrics["total_outstanding"] = f"{total_outstanding_val:,.2f}" if total_outstanding_val > 0 else "0.00"
            
        if (self.summary_metrics.get("total_overdue") == "N/A" or not self.summary_metrics.get("total_overdue") or self.summary_metrics.get("total_overdue") == "0.00") and account_list:
            total_overdue_val = sum(self._clean_val(a.get("Overdue Amount", a.get("Overdue Amt", 0))) for a in account_list)
            self.summary_metrics["total_overdue"] = f"{total_overdue_val:,.2f}" if total_overdue_val > 0 else "0.00"

        self.accounts = account_list

    def _fallback_account_parse(self) -> list:
        """Regex-based fallback for accounts when table extraction fails."""
        account_list = []
        combined = self._combined_text()
        blocks = re.split(
            r"(?=Account\s*(?:#|No|Number)|Account\s*Type|Trade\s*Line|Lender\s*Name|Member\s*Name|Loan\s*Type|Date\s*Opened|Disbursed\s*Date)",
            combined, flags=re.IGNORECASE
        )
        for block in blocks:
            if not block.strip():
                continue
            
            # Group-based checklist to verify this block is indeed an account
            labels_group = [
                ["type", "product", "loan"],
                ["balance", "outstanding", "curr bal", "curr balance", "bal"],
                ["overdue", "delinquent", "default"],
                ["status", "active", "closed", "reported"]
            ]
            hits = 0
            block_lower = block.lower()
            for group in labels_group:
                if any(kw in block_lower for kw in group):
                    hits += 1
            if hits < 2:  # require at least two categories to be present
                continue

            def rx(patterns, default="-"):
                for pat in patterns:
                    m = re.search(pat, block, re.IGNORECASE)
                    if m:
                        return m.group(1).split("\n")[0].strip()
                return default

            acct_type = rx([
                r"(?:Account|Loan)\s*Type\s*[:\-]?\s*([A-Za-z0-9\s\-\/]+)",
                r"Product\s*[:\-]?\s*([A-Za-z0-9\s\-\/]+)",
                r"\bType\s*[:\-]?\s*([A-Za-z0-9\s\-\/]+)"
            ], "Unknown")
            
            if acct_type == "Unknown":
                for kw in ["credit card", "personal loan", "consumer loan", "home loan", "housing loan", "auto loan", "vehicle loan", "car loan", "gold loan", "overdraft", "business loan", "mudra loan", "education loan"]:
                    if kw in block_lower:
                        acct_type = kw.title()
                        break
                        
            lender = rx([
                r"(?:Lender|Member|Creditor|Bank)\s*(?:Name)?\s*[:\-]?\s*([A-Za-z0-9\s\,\.\-\&\/]+)",
                r"Institution\s*[:\-]?\s*([A-Za-z0-9\s\,\.\-\&\/]+)"
            ])
            if lender == "-":
                for line in block.split("\n"):
                    if any(kw in line.lower() for kw in ["bank", "finance", "capital", "ltd", "cooperative", "credit", "finser", "finserv", "sbi", "hdfc", "icici", "axis"]):
                        cleaned_line = re.sub(r"^(?:Lender|Member|Bank|Name|Institution|Account)\s*[:\-]?\s*", "", line, flags=re.IGNORECASE).strip()
                        if 3 < len(cleaned_line) < 50:
                            lender = cleaned_line
                            break
                            
            status = rx([
                r"(?:Account\s*)?Status\s*[:\-]?\s*([A-Za-z\s]+)",
                r"Current\s*Status\s*[:\-]?\s*([A-Za-z\s]+)"
            ])
            if status == "-":
                if "active" in block_lower:
                    status = "Active"
                elif "closed" in block_lower:
                    status = "Closed"
                elif "settled" in block_lower:
                    status = "Settled"
                elif "written off" in block_lower or "write-off" in block_lower:
                    status = "Written Off"
                    
            security = rx([r"Security(?:\s*Status)?\s*[:\-]?\s*([A-Za-z\-\s]+)"])
            
            disb_date = rx([
                r"(?:Disbursed?\s*Date|Date\s*Opened|Open\s*Date|Disbursal\s*Date|Sanction\s*Date)\s*[:\-]?\s*(\d{2}[-\/\s][A-Za-z0-9]{2,3}[-\/\s]\d{2,4})",
                r"(?:Disbursed?\s*Date|Date\s*Opened|Open\s*Date|Disbursal\s*Date|Sanction\s*Date)\s*[:\-]?\s*(\d{2}[-\/]\d{2}[-\/]\d{2,4})",
                r"Date\s*of\s*(?:Disbursal|Opening)\s*[:\-]?\s*(\d{2}[-\/\s][A-Za-z0-9]{2,3}[-\/\s]\d{2,4})"
            ])
            
            last_rep = rx([
                r"(?:Last\s*Reported|Date\s*Reported|Last\s*Updated|Reporting\s*Date)\s*[:\-]?\s*(\d{2}[-\/\s][A-Za-z0-9]{2,3}[-\/\s]\d{2,4})",
                r"(?:Last\s*Reported|Date\s*Reported|Last\s*Updated|Reporting\s*Date)\s*[:\-]?\s*(\d{2}[-\/]\d{2}[-\/]\d{2,4})"
            ])
            
            disb_amt = rx([
                r"(?:Disbursed?\s*Amount|Sanctioned\s*Amount|Credit\s*Limit|Sanction\s*Limit)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.\-]+)",
                r"Limit\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.\-]+)"
            ])
            
            curr_bal = rx([
                r"(?:Current\s*Balance|Outstanding(?:\s*Balance)?)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.\-]+)",
                r"Balance\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.\-]+)"
            ])
            
            overdue = rx([
                r"(?:Total\s*)?Overdue\s*(?:Amount|Amt|Balance)?\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.\-]+)",
                r"Amount\s*Overdue\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.\-]+)"
            ])
            
            wo_amt = rx([
                r"(?:Written?.?off|Write.?off)\s*(?:Amount|Amt)?\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.\-]+)"
            ])
            
            wo_status = rx([
                r"(?:WO|Written?.?off)\s*/?\s*Settled\s*Status\s*[:\-]?\s*([A-Za-z\s\(\)]+)"
            ])
            
            last_pmt = rx([
                r"Last\s*Payment\s*(?:Date)?\s*[:\-]?\s*(\d{2}[-\/\s][A-Za-z0-9]{2,3}[-\/\s]\d{2,4})",
                r"Last\s*Payment\s*(?:Date)?\s*[:\-]?\s*(\d{2}[-\/]\d{2}[-\/]\d{2,4})"
            ])
            
            ownership = rx([r"Ownership\s*[:\-]?\s*([A-Za-z]+)"])
            occupation = rx([r"Occupation\s*[:\-]?\s*([A-Za-z\s]+)"])
            
            high_credit = rx([
                r"(?:High\s*Credit|Highest\s*Balance|High\s*Balance)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.\-]+)",
                r"High\s*Credit\s*Limit\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.\-]+)"
            ])
            
            interest_rate = rx([
                r"(?:Interest\s*Rate|Rate\s*of\s*Interest|ROI|Rate)\s*[:\-]?\s*([0-9\.\%\s\-]+)"
            ])
            
            installment = rx([
                r"(?:Installment\s*Amount|Installment|EMI\s*Amount|EMI|Monthly\s*Payment)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([0-9\,\.\-]+)"
            ])
            
            dpd_history = rx([
                r"(?:DPD\s*History|DPD|Days\s*Past\s*Due|Payment\s*History)\s*[:\-]?\s*([0-9Xx\/\s\-]+)"
            ])

            if lender != "-" or acct_type != "Unknown":
                if len(lender) < 60 and "report" not in lender.lower() and "crif" not in lender.lower():
                    asset_class = rx([
                        r"Asset\s*Classification\s*[:\-]?\s*([A-Za-z\s\-]+)",
                        r"NPA\s*Classification\s*[:\-]?\s*([A-Za-z\s\-]+)",
                        r"Asset\s*Class\s*[:\-]?\s*([A-Za-z\s\-]+)",
                    ])
                    account_list.append({
                        "Lender": lender,
                        "Account Number": rx([
                            r"(?:Account\s*No|Account\s*#|Account\s*Number|Acct\s*No)\s*[:\-]?\s*([A-Za-z0-9Xx\*]+)",
                            r"Acct\s*#\s*[:\-]?\s*([A-Za-z0-9Xx\*]+)"
                        ]),
                        "Account Type": acct_type,
                        "Status": status,
                        "Security": security,
                        "Date Opened": disb_date,
                        "Last Reported": last_rep,
                        "Credit Limit/Sanctioned": disb_amt,
                        "Current Balance": curr_bal,
                        "Overdue Amount": overdue,
                        "Write-off Amount": wo_amt,
                        "WO/Settled Status": wo_status,
                        "Last Payment": last_pmt,
                        "Ownership": ownership,
                        "Occupation": occupation,
                        "High Credit": high_credit,
                        "Asset Classification": asset_class,
                        "Interest Rate": interest_rate,
                        "Installment Amount": installment,
                        "DPD History / Payment History": dpd_history,
                    })
        return account_list

    def _extract_structured_inquiries(self):
        inquiry_list = []
        last_header_map = None
        last_col_count = None

        INQ_TRIGGER_KW = ["inquiry date", "inquirer", "purpose", "amount", "inquiry amount"]
        ACCT_KW = ["account type", "lender", "current balance", "outstanding", "overdue", "disbursed"]

        for page_num, tables in sorted(self.tables_by_page.items()):
            for table in tables:
                if not table:
                    continue
                first_row = [str(c).strip().lower() for c in table[0] if c]
                is_inq = False

                inq_hit = sum(1 for kw in INQ_TRIGGER_KW if any(kw in h for h in first_row))
                acct_hit = sum(1 for kw in ACCT_KW if any(kw in h for h in first_row))

                if inq_hit >= 2 and acct_hit < 2:
                    is_inq = True
                    header_map = {}
                    for idx, c in enumerate(table[0]):
                        if not c:
                            continue
                        h = str(c).strip().lower()
                        if "date" in h:
                            header_map["date"] = idx
                        elif any(kw in h for kw in ["inquirer", "bank", "member", "institution", "lender"]):
                            header_map["inquirer"] = idx
                        elif "purpose" in h or "type" in h:
                            header_map["purpose"] = idx
                        elif "amount" in h:
                            header_map["amount"] = idx
                    last_header_map = header_map
                    last_col_count = len(table[0])
                    start_row_idx = 1
                else:
                    if last_header_map and len(table[0]) == last_col_count and acct_hit < 2:
                        is_inq = True
                        header_map = last_header_map
                        start_row_idx = 0

                if is_inq:
                    for row in table[start_row_idx:]:
                        if not row or len(row) <= max(header_map.values(), default=0):
                            continue

                        def gv(key, default=""):
                            if key in header_map:
                                c = row[header_map[key]]
                                return str(c).strip() if c is not None else default
                            return default

                        dt = gv("date", "N/A")
                        inquirer = gv("inquirer", "Unknown")
                        purpose = gv("purpose", "N/A")
                        amt = gv("amount", "0")

                        if inquirer != "Unknown" or dt != "N/A":
                            inquiry_list.append({
                                "Inquiry Date": dt,
                                "Inquirer": inquirer,
                                "Purpose": purpose,
                                "Amount": amt,
                            })

        # Fallback: text parsing
        if not inquiry_list:
            combined = self._combined_text()
            in_section = False
            for line in combined.split("\n"):
                if any(kw in line.lower() for kw in ["inquiry history", "recent inquiries", "inquiry details"]):
                    in_section = True
                    continue
                if in_section:
                    if any(kw in line.lower() for kw in ["account details", "disclaimer", "glossary", "summary"]):
                        in_section = False
                        continue
                    dt_m = re.search(r"\b(\d{2}[-\/]\d{2}[-\/]\d{2,4})\b", line)
                    amt_m = re.search(r"\b(\d+[\,\d]*)\b", line)
                    if dt_m and amt_m:
                        parts = [p.strip() for p in line.split("  ") if p.strip()]
                        if len(parts) >= 3:
                            dt_v = dt_m.group(1)
                            amt_v = amt_m.group(1)
                            inq_v = "Unknown"
                            purp_v = "N/A"
                            for p in parts:
                                if p not in [dt_v, amt_v] and not re.match(r"^\d+$", p):
                                    if any(kw in p.lower() for kw in ["loan", "card", "credit", "personal"]):
                                        purp_v = p
                                    else:
                                        inq_v = p
                            inquiry_list.append({
                                "Inquiry Date": dt_v,
                                "Inquirer": inq_v,
                                "Purpose": purp_v,
                                "Amount": amt_v,
                            })

        self.inquiries = inquiry_list

    def _extract_status_details(self):
        """Extract bureau service status details (CNS-SCORE, MFI, etc.) from the PDF."""
        combined = self._combined_text()
        status_list = []

        services = [
            "CNS-SCORE", "CNS-INCOME", "MFI-INDV", "MFI-GRP", "CNS_INDV",
            "INQUIRY-HISTORY", "CRIF-SCORE"
        ]
        status_words = ["SUCCESS", "NO RESPONSE FOUND", "NO RECORD FOUND", "FAILURE", "ERROR"]

        for svc in services:
            pat = rf"{re.escape(svc)}\s*[:\-]?\s*([A-Za-z\s]+?)(?=\n|{re.escape(svc)}|$)"
            m = re.search(pat, combined, re.IGNORECASE)
            if m:
                sv = m.group(1).strip().upper()
                # Normalize
                if not any(w in sv for w in status_words):
                    sv = "SUCCESS" if "success" in sv.lower() else sv
                status_list.append({"option": svc, "status": sv})

        # Generic: any line with STATUS: XXX
        if not status_list:
            for line in combined.split("\n"):
                for svc in services:
                    if svc in line.upper():
                        for sw in status_words:
                            if sw in line.upper():
                                status_list.append({"option": svc, "status": sw})
                                break

        self.status_details = status_list
