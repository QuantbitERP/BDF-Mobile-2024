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

        attendance_report = run("Customer Ledger Summary",filters=filters,ignore_prepared_report=True)
        frappe.msgprint(str(attendance_report))
        if attendance_report:
            for entry in attendance_report.get("result"):
               if isinstance(entry, dict): 
                processed_entry = {
                    "party": entry.get("party")if entry.get("party") else '',
                    "party_name": entry.get("party_name")if entry.get("party") else '',
                    "opening_balance": float(entry.get("opening_balance", 0))if entry.get("opening_balance") else 0.0,
                    "invoiced_amount": float(entry.get("invoiced_amount", 0))if entry.get("invoiced_amount") else 0.0,
                    "bank_receipts": float(entry.get("bank_receipts", 0))if entry.get("bank_receipts") else 0.0,
                    "cash_receipts": float(entry.get("cash_receipts", 0))if entry.get("cash_receipts") else 0.0,
                    "closing_balance": float(entry.get("closing_balance", 0))if entry.get("closing_balance") else 0.0,
                }
                processed_data.append(processed_entry)
            return gen_response(200, "Customer Ledger get successfully", processed_data)
    except Exception as e:
        return exception_handel(e)


@frappe.whitelist()
def run_payment_ledger_report(from_date, to_date,party_type=None):
    try:
        processed_data = []
        global_defaults = get_global_defaults()
        company = global_defaults.get("default_company")
        filters = {
            "period_start_date": from_date,
            "period_end_date": to_date,
            "company": company,
            "party_type":party_type
           
        }

        from frappe.desk.query_report import run

        attendance_report = run("Payment Ledger", filters=filters,)
        frappe.msgprint(str(len(attendance_report)))
        if attendance_report:
            for entry in attendance_report.get("result"):
                if isinstance(entry, dict):
                    processed_entry = {
                        "posting_date": entry.get("posting_date") if entry.get("posting_date") else '',
                        "account": entry.get("account") if entry.get("account") else '',
                        "party_type": entry.get("party_type") if entry.get("party_type") else '',
                        "party": entry.get("party") if entry.get("party") else '',
                        "voucher_type": entry.get("voucher_type") if entry.get("voucher_type") else '',
                        "voucher_no": entry.get("voucher_no") if entry.get("voucher_no") else '',
                        "against_voucher_type": entry.get("against_voucher_type") if entry.get("against_voucher_type") else '',
                        "against_voucher_no": entry.get("against_voucher_no") if entry.get("against_voucher_no") else '',
                        "currency": entry.get("currency") if entry.get("currency") else '',
                        "amount": float(entry.get("amount")) if entry.get("amount") else 0.0,
                    }
                    processed_data.append(processed_entry)
            return gen_response(200, "Payment Ledger get successfully", processed_data)
    except Exception as e:
        return exception_handel(e)

