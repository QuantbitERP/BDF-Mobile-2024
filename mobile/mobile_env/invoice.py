import json
import frappe
from frappe import _
from erpnext.utilities.product import get_price
from erpnext.accounts.utils import getdate
from mobile.mobile_env.app_utils import (
    gen_response,
    ess_validate,
    get_ess_settings,
    prepare_json_data,
    get_global_defaults,
    exception_handel,
)
from erpnext.accounts.party import (get_dashboard_info,get_party_account)
from erpnext.controllers.queries import get_income_account



@frappe.whitelist()
def get_customer_list():
    try:
        customer_list = frappe.get_list(
            "Customer",
            fields=["name", "customer_name", "workflow_state", "default_price_list"],
            filters={"workflow_state": "Approved"}
        )
        for customer in customer_list:
            routes = frappe.get_value(
                "Dynamic Link",
                {
                    "link_doctype": "Route Master",
                    "parenttype": "Customer",
                    "parent": customer.name,
                },
                'link_name'
            )
            customer["routes"] = routes
            route_warehouse=frappe.get_value(
                "Route Master",
                routes,
                'source_warehouse'
            )
            customer["route_warehouse"]=route_warehouse


        gen_response(200, "Customer list fetched successfully", customer_list)
    except Exception as e:
        return exception_handel(e)


"""get item list for mobile app to make order"""

@frappe.whitelist()
def get_item_list(warehouse=None, price_list=None,customer=None):
    # Set default warehouse and price list if not provided
    if not warehouse:
        warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
        
    if not price_list:
        price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
        
    try:
        # Fetching the party specific items
        party_item_list = frappe.get_all(
            "Party Specific Item",
            filters={
                "party_type": "Customer",
                "party": customer,
                "restrict_based_on": "Item"
            },
            pluck="based_on_value"
        )
        
        frappe.msgprint(str(party_item_list))

        # If no party-specific items are found, get all items
        if not party_item_list:
            frappe.msgprint("No party-specific items found, retrieving all items.")
            item_filters = {
                "is_sales_item": 1,
                "has_variants": 0,
                "disabled": 0
            }
        else:
            item_filters = {
                "is_sales_item": 1,
                "has_variants": 0,
                "disabled": 0,
                "name": ["in", party_item_list]
            }

        # Fetching item details
        item_list = frappe.get_list(
            "Item",
            fields=[
                "name",
                "item_name",
                "item_code",
                "image",
                "sales_uom",
                "stock_uom"
            ],
            filters=item_filters
        )
        items = get_items_data(item_list,warehouse,price_list,customer)
        gen_response(200, "Item list get successfully", items)
    except Exception as e:
        exception_handel(e)


def get_items_data(items,warehouse,price_list,customer):
    items_data = []
    for item in items:
        item_data = {
            "name": item.name,
            "item_name": item.item_name,
            "item_code": item.item_code,
            "image": item.image,
            "uom":item.sales_uom if item.sales_uom else item.stock_uom,
            "actual_qty": float(get_actual_qty(item.item_code,warehouse)),
            "rate": get_item_rate(item.item_code,price_list,customer)  # Fetch rate
        }
        items_data.append(item_data)
    return items_data


def get_actual_qty(item_code,warehouse):
    bin_data = frappe.get_all(
        "Bin",
        filters={"item_code": item_code,"warehouse":warehouse},
        fields=["actual_qty", "warehouse"]
    )
    if bin_data:
        return bin_data[0].get("actual_qty", 0)
    else:
        return 0


def get_item_rate(item_code, price_list, customer):
    customer_group = frappe.get_value("Customer", customer, "customer_group")
    global_defaults = get_global_defaults()
    company = global_defaults.get("default_company")
    item_price = get_price(item_code=item_code, price_list=price_list, customer_group=customer_group, company=company)
    if item_price and "formatted_price_sales_uom" in item_price:
        formatted_price = item_price["formatted_price_sales_uom"].replace('₹', '').replace(',', '').strip()
        return float(formatted_price)
    else:
        return 0.0


# Continue with your code as needed
    
@frappe.whitelist()
def prepare_order_totals(**kwargs):
    try:
        data = kwargs
        if not data.get("customer"):
            return gen_response(500, "Customer is required.")

        source_warehouse=data.get('set_warehouse')
        if source_warehouse:
            for item in data.get("items"):
                item["warehouse"] = source_warehouse
        global_defaults = get_global_defaults()
        company = global_defaults.get("default_company")
        sales_invoice_doc = frappe.get_doc(dict(doctype="Sales Invoice", company=company))
        sales_invoice_doc.update(data)
        sales_invoice_doc.run_method("set_missing_values")
        sales_invoice_doc.run_method("calculate_taxes_and_totals")
        order_data = (
            prepare_json_data(
                [
                    "taxes_and_charges",
                    "total_taxes_and_charges",
                    "net_total",
                    "discount_amount",
                    "grand_total",
                ],
                json.loads(sales_invoice_doc.as_json()),
            ),
        )
        gen_response(200, "invoice details get successfully", order_data)
    except Exception as e:
        return exception_handel(e)


@frappe.whitelist()
def get_warehouselist():
    global_defaults = get_global_defaults()
    company = global_defaults.get("default_company")
    try:
        warehouselist = frappe.get_list(
            "Warehouse",
            # fields=["name", "company"],
            filters={"company": company,"is_group":0}
        )
        
        gen_response(200, "warehouse list successfully", warehouselist)
    except Exception as e:
        exception_handel(e)

@frappe.whitelist()
def get_invoice_list():
    try:
        invoice_list = frappe.get_list(
            "Sales Invoice",
            fields=[
                "name",
                "customer_name",
                "DATE_FORMAT(due_date, '%d-%m-%Y') as due_date",
                "grand_total",
                "status",
                "total_qty",
            ],
             order_by='creation desc',
        )
        gen_response(200, "Invoice list get successfully", invoice_list)
    except Exception as e:
        return exception_handel(e)




@frappe.whitelist()
def create_invoice(**kwargs):
    try:
        data = kwargs
        if not data.get("customer"):
            return gen_response(500, "Customer is required.")
        if not data.get("items") or len(data.get("items")) == 0:
            return gen_response(500, "Please select items to proceed.")
        if not data.get("due_date"):
            return gen_response(500, "Please select due_date to proceed.")

        source_warehouse=data.get('set_warehouse')
        if source_warehouse:
            for item in data.get("items"):
                item["warehouse"] = source_warehouse

        global_defaults = get_global_defaults()
        company = global_defaults.get("default_company")

        if data.get("name"):
            if not frappe.db.exists("Sales Invoice", data.get("name"), cache=True):
                return gen_response(500, "Invalid invoice id.")
            sales_invoice_doc = frappe.get_doc("Sales Invoice", data.get("name"))
            sales_invoice_doc.update(data)
            sales_invoice_doc.run_method("set_missing_values")
            sales_invoice_doc.run_method("calculate_taxes_and_totals")
            sales_invoice_doc.save()
            gen_response(200, "Sales Invoice updated successfully.", sales_invoice_doc)
           
        else:
            sales_invoice_doc = frappe.get_doc(dict(doctype="Sales Invoice", company=company))
            sales_invoice_doc.update(data)
            sales_invoice_doc.run_method("set_missing_values")
            sales_invoice_doc.run_method("calculate_taxes_and_totals")
            sales_invoice_doc.insert()
            
            if data.get("attachments") is not None:
                for file in data.get("attachments"):
                    file_doc = frappe.get_doc(
                        {
                            "doctype": "File",
                            "file_url": file.get("file_url"),
                            "attached_to_doctype": "Sales Invoice",
                            "attached_to_name": sales_invoice_doc.name,
                        }
                    )
                    file_doc.insert(ignore_permissions=True)
            gen_response(200, "Sales Invoice created successfully.", sales_invoice_doc)

    except Exception as e:
        return exception_handel(e)