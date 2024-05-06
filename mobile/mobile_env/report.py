import json
import os
import calendar
import frappe
from frappe import _

from frappe.utils import cstr, now, today
from frappe.auth import LoginManager
from frappe.utils import (
    cstr,
    get_date_str,
    today,
    nowdate,
    getdate,
    now_datetime,
    get_first_day,
    get_last_day,
    date_diff,
    flt,
    pretty_date,
    fmt_money,
)
from frappe.utils.data import nowtime
from mobile.mobile_env.app_utils import (
    gen_response,
    generate_key,
    role_profile,
    ess_validate,
    get_employee_by_user,
    validate_employee_data,
    get_ess_settings,
    get_global_defaults,
    exception_handel,
)



    
@frappe.whitelist()
def run_customer_ledger_report(from_date, to_date, customer, customer_group):
    try:
        processed_data = []
        global_defaults = get_global_defaults()
        company = global_defaults.get("default_company")
        filters = {
            "from_date": from_date,
            "to_date": to_date,
            "company": company,
            "customer_group": customer_group if customer_group else None,
            "party": customer if customer else None
        }

        from frappe.desk.query_report import run

        attendance_report = run("Customer Ledger Summary", filters=filters)

        if attendance_report:
            for entry in attendance_report.get("result"):
               if isinstance(entry, dict): 
                processed_entry = {
                    "party": entry.get("party"),
                    "party_name": entry.get("party_name"),
                    "opening_balance": float(entry.get("opening_balance", 0)),
                    "invoiced_amount": float(entry.get("invoiced_amount", 0)),
                    "bank_receipts": float(entry.get("bank_receipts", 0)),
                    "cash_receipts": float(entry.get("cash_receipts", 0)),
                    "closing_balance": float(entry.get("closing_balance", 0)),
                }
                processed_data.append(processed_entry)
            return gen_response(200, "Customer Ledger get successfully", processed_data)
    except Exception as e:
        return exception_handel(e)


@frappe.whitelist()
def run_payment_ledger_report(from_date, to_date):
    try:
        processed_data = []
        global_defaults = get_global_defaults()
        company = global_defaults.get("default_company")
        filters = {
            "from_date": "2024-04-01",
            "to_date": "2024-04-15",
            "company": company,
            
        }

        from frappe.desk.query_report import run

        attendance_report = run("Payment Ledger", filters=filters)
        # frappe.throw(str(attendance_report.get("result")))
        if attendance_report:
            for entry in attendance_report.get("result"):
                
                if isinstance(entry, dict): 
                    processed_entry = {
                        "posting_date": entry.get("posting_date"),
                        "account": entry.get("account"),
                        "party_type": entry.get("party_type"),
                        "party": entry.get("party"),
                        "voucher_type": entry.get("voucher_type"),
                        "voucher_no": entry.get("voucher_no"),
                        "currency": entry.get("currency"),
                        "amount":float(entry.get("amount"))
                    }
                    processed_data.append(processed_entry)
                return gen_response(200, "Payment Ledger get successfully", processed_data)
    except Exception as e:
        return exception_handel(e)
