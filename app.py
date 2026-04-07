import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import date

st.set_page_config(page_title="Business Ledger", layout="wide")

st.title("📑 Multi-Date Ledger & Payment Tracker")

# Initialize session state
if 'data_by_date' not in st.session_state:
    st.session_state.data_by_date = {} # Store items, tax_rate, and payment_received
if 'editing_key' not in st.session_state:
    st.session_state.editing_key = None 

# --- 1. Sidebar: Date & Payment Settings ---
with st.sidebar:
    st.header("📅 Entry Settings")
    active_date = st.date_input("Select Working Date", value=date.today())
    active_date_str = active_date.strftime("%Y-%m-%d")
    
    # Initialize date entry if not exists
    if active_date_str not in st.session_state.data_by_date:
        st.session_state.data_by_date[active_date_str] = {
            "items": [],
            "tax_rate": 0.0,
            "payment_received": 0.0
        }
    
    st.divider()
    st.subheader(f"Financials for {active_date_str}")
    
    # Tax and Payment inputs for the specific date
    st.session_state.data_by_date[active_date_str]["tax_rate"] = st.number_input(
        "Tax (%) for this Date", 
        min_value=0.0, step=0.1, 
        value=st.session_state.data_by_date[active_date_str]["tax_rate"],
        key=f"tax_in_{active_date_str}"
    )
    
    st.session_state.data_by_date[active_date_str]["payment_received"] = st.number_input(
        "Payment Received (Rs )", 
        min_value=0.0, step=1.0, 
        value=st.session_state.data_by_date[active_date_str]["payment_received"],
        key=f"pay_in_{active_date_str}"
    )

# --- 2. Product Entry Section ---
with st.expander(f"➕ Add/Edit Item for {active_date_str}", expanded=True):
    edit_info = st.session_state.editing_key
    current_item = None
    if edit_info and edit_info[0] == active_date_str:
        current_item = st.session_state.data_by_date[active_date_str]["items"][edit_info[1]]

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        desc = st.text_input("Item Description", value=current_item['Description'] if current_item else "")
    with col2:
        qty = st.number_input("Qty", min_value=1, step=1, value=current_item['Quantity'] if current_item else 1)
    with col3:
        rate = st.number_input("Rate", min_value=0.0, step=0.01, value=current_item['Rate'] if current_item else 0.0)

    if st.button("Update Item" if edit_info else "Add Item", type="primary"):
        if desc:
            new_entry = {"Description": desc, "Quantity": qty, "Rate": rate, "Amount": qty * rate}
            if edit_info:
                st.session_state.data_by_date[active_date_str]["items"][edit_info[1]] = new_entry
                st.session_state.editing_key = None
            else:
                st.session_state.data_by_date[active_date_str]["items"].append(new_entry)
            st.rerun()

# --- 3. Data Display & Daily Calculations ---
all_data_for_export = []
grand_total_receivable = 0
grand_total_received = 0

if st.session_state.data_by_date:
    for d_str, data in sorted(st.session_state.data_by_date.items(), reverse=True):
        if not data["items"]: continue # Skip empty dates
        
        with st.container():
            st.markdown(f"### 🗓️ Date: {d_str}")
            
            # Table Display
            df_day = pd.DataFrame(data["items"])
            st.table(df_day)
            
            # Action Buttons Row
            cols = st.columns(len(data["items"]))
            for i, item in enumerate(data["items"]):
                if st.button(f"Edit {item['Description']}", key=f"e_{d_str}_{i}"):
                    st.session_state.editing_key = (d_str, i)
                    st.rerun()

            # Daily Math
            subtotal = df_day['Amount'].sum()
            tax_amount = subtotal * (data["tax_rate"] / 100)
            total_with_tax = subtotal + tax_amount
            due = total_with_tax - data["payment_received"]
            
            # Update Grand Totals
            grand_total_receivable += total_with_tax
            grand_total_received += data["payment_received"]

            # Daily Summary Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Subtotal", f"Rs {subtotal:,.2f}")
            m2.metric(f"Tax ({data['tax_rate']}%)", f"Rs {tax_amount:,.2f}")
            m3.metric("Received", f"Rs {data['payment_received']:,.2f}")
            m4.metric("Pending Due", f"Rs {due:,.2f}", delta=-due, delta_color="inverse")
            
            # Data for Excel
            for item in data["items"]:
                row = item.copy()
                row.update({"Date": d_str, "Tax %": data["tax_rate"], "Paid": data["payment_received"]})
                all_data_for_export.append(row)
            st.divider()

# --- 4. Grand Summary & Export ---
if all_data_for_export:
    st.subheader("🏁 Overall Business Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Billed (Inc Tax)", f"Rs {grand_total_receivable:,.2f}")
    c2.metric("Total Payments Received", f"Rs {grand_total_received:,.2f}")
    c3.metric("Total Outstanding Dues", f"Rs {grand_total_receivable - grand_total_received:,.2f}")

    def to_excel():
        df_export = pd.DataFrame(all_data_for_export)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Ledger')
        return output.getvalue()

    st.download_button(
        "📥 Download Full Ledger (Excel)",
        data=to_excel(),
        file_name=f"Ledger_Export_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
