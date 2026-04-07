import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import date

st.set_page_config(page_title="Professional Ledger", layout="wide")

st.title("📑 Business Ledger & Multi-Sheet Exporter")

# --- Session State Initialization ---
if 'data_by_date' not in st.session_state:
    st.session_state.data_by_date = {}
if 'editing_key' not in st.session_state:
    st.session_state.editing_key = None 

# --- 1. Sidebar: Date & Financial Settings ---
with st.sidebar:
    st.header("📅 Entry Settings")
    active_date = st.date_input("Select Working Date", value=date.today())
    active_date_str = active_date.strftime("%Y-%m-%d")
    
    if active_date_str not in st.session_state.data_by_date:
        st.session_state.data_by_date[active_date_str] = {
            "items": [],
            "tax_rate": 0.0,
            "payment_received": 0.0
        }
    
    st.divider()
    st.subheader(f"Financials: {active_date_str}")
    
    st.session_state.data_by_date[active_date_str]["tax_rate"] = st.number_input(
        "Tax Rate (%)", min_value=0.0, step=0.1, 
        value=st.session_state.data_by_date[active_date_str]["tax_rate"],
        key=f"tax_{active_date_str}"
    )
    
    st.session_state.data_by_date[active_date_str]["payment_received"] = st.number_input(
        "Payment Received (Rs )", min_value=0.0, step=1.0, 
        value=st.session_state.data_by_date[active_date_str]["payment_received"],
        key=f"pay_{active_date_str}"
    )

# --- 2. Input Form (Add / Update) ---
edit_info = st.session_state.editing_key
current_item = None
if edit_info and edit_info[0] == active_date_str:
    current_item = st.session_state.data_by_date[active_date_str]["items"][edit_info[1]]

with st.expander("📝 Add / Edit Product Details", expanded=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        desc = st.text_input("Product Description", value=current_item['Description'] if current_item else "")
    with c2:
        qty = st.number_input("Quantity", min_value=1, value=current_item['Quantity'] if current_item else 1)
    with c3:
        rate = st.number_input("Rate (Rs )", min_value=0.0, value=current_item['Rate'] if current_item else 0.0)

    btn_col1, btn_col2 = st.columns([1, 5])
    if btn_col1.button("Update" if edit_info else "Add Item", type="primary"):
        if desc:
            new_entry = {"Description": desc, "Quantity": qty, "Rate": rate, "Amount": qty * rate}
            if edit_info:
                st.session_state.data_by_date[active_date_str]["items"][edit_info[1]] = new_entry
                st.session_state.editing_key = None
            else:
                st.session_state.data_by_date[active_date_str]["items"].append(new_entry)
            st.rerun()
    
    if edit_info and btn_col2.button("Cancel Edit"):
        st.session_state.editing_key = None
        st.rerun()

# --- 3. Data Display & Calculations ---
st.divider()
grand_total_billed = 0
grand_total_paid = 0
export_items = []
export_dues = []

if st.session_state.data_by_date:
    for d_str in sorted(st.session_state.data_by_date.keys(), reverse=True):
        day_data = st.session_state.data_by_date[d_str]
        if not day_data["items"]: continue
        
        st.subheader(f"🗓️ Date: {d_str}")
        
        h1, h2, h3, h4, h5 = st.columns([3, 1, 1, 1, 1.5])
        h1.write("**Item**")
        h2.write("**Qty**")
        h3.write("**Rate**")
        h4.write("**Total**")
        h5.write("**Actions**")

        day_subtotal = 0
        for i, item in enumerate(day_data["items"]):
            day_subtotal += item["Amount"]
            c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1.5])
            c1.write(item["Description"])
            c2.write(str(item["Quantity"]))
            c3.write(f"Rs {item['Rate']:,.2f}")
            c4.write(f"Rs {item['Amount']:,.2f}")
            
            edit_btn, del_btn = c5.columns(2)
            if edit_btn.button("✏️", key=f"edit_{d_str}_{i}"):
                st.session_state.editing_key = (d_str, i)
                st.rerun()
            if del_btn.button("🗑️", key=f"del_{d_str}_{i}"):
                st.session_state.data_by_date[d_str]["items"].pop(i)
                st.rerun()

            # Itemized List for Excel
            item_row = item.copy()
            item_row["Date"] = d_str
            export_items.append(item_row)

        # Day Financials
        tax_val = day_subtotal * (day_data["tax_rate"] / 100)
        day_total = day_subtotal + tax_val
        day_paid = day_data["payment_received"]
        day_pending = day_total - day_paid
        
        grand_total_billed += day_total
        grand_total_paid += day_paid

        # Dues Summary for Excel
        export_dues.append({
            "Date": d_str,
            "Subtotal": day_subtotal,
            "Tax (%)": day_data["tax_rate"],
            "Tax Amount": tax_val,
            "Total Billed": day_total,
            "Amount Paid": day_paid,
            "Pending Due": day_pending
        })

        s1, s2, s3, s4 = st.columns(4)
        s1.write(f"**Subtotal:** Rs {day_subtotal:,.2f}")
        s2.write(f"**Tax ({day_data['tax_rate']}%):** Rs {tax_val:,.2f}")
        s3.write(f"**Paid:** Rs {day_paid:,.2f}")
        s4.markdown(f"**Pending:** :red[Rs {day_pending:,.2f}]")
        st.divider()

# --- 4. Grand Summary & Multi-Sheet Export ---
if export_items:
    st.subheader("🏁 Overall Business Summary")
    g1, g2, g3 = st.columns(3)
    g1.metric("Total Billed", f"Rs {grand_total_billed:,.2f}")
    g2.metric("Total Received", f"Rs {grand_total_paid:,.2f}")
    g3.metric("Total Outstanding", f"Rs {grand_total_billed - grand_total_paid:,.2f}")

    def get_excel_file():
        df_ledger = pd.DataFrame(export_items)[['Date', 'Description', 'Quantity', 'Rate', 'Amount']]
        df_dues = pd.DataFrame(export_dues)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet 1: Itemized Ledger
            df_ledger.to_excel(writer, index=False, sheet_name='Itemized_Ledger')
            # Sheet 2: Dues Summary
            df_dues.to_excel(writer, index=False, sheet_name='Dues_Summary')
        return output.getvalue()

    st.download_button(
        "📥 Download Multi-Sheet Excel Report",
        data=get_excel_file(),
        file_name=f"Ledger_Report_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
