import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import date

st.set_page_config(page_title="Ultimate Ledger", layout="wide")

st.title("📑 Business Ledger & Debt Tracker")
st.write("Manage products by date, apply tax, and track payments received.")

# --- Session State Initialization ---
if 'data_by_date' not in st.session_state:
    st.session_state.data_by_date = {}
if 'editing_key' not in st.session_state:
    st.session_state.editing_key = None # Format: (date_str, index)

# --- 1. Sidebar: Date & Financial Settings ---
with st.sidebar:
    st.header("📅 Entry Settings")
    active_date = st.date_input("Select Working Date", value=date.today())
    active_date_str = active_date.strftime("%Y-%m-%d")
    
    # Initialize the date in dictionary if new
    if active_date_str not in st.session_state.data_by_date:
        st.session_state.data_by_date[active_date_str] = {
            "items": [],
            "tax_rate": 0.0,
            "payment_received": 0.0
        }
    
    st.divider()
    st.subheader(f"Financials: {active_date_str}")
    
    # Global settings for the active date
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
# Check if we are currently editing an item on the ACTIVE date
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

# --- 3. Management Table & Daily Totals ---
st.divider()
grand_total_billed = 0
grand_total_paid = 0
export_list = []

if st.session_state.data_by_date:
    # Sort dates to show newest first
    for d_str in sorted(st.session_state.data_by_date.keys(), reverse=True):
        day_data = st.session_state.data_by_date[d_str]
        if not day_data["items"]: continue
        
        st.subheader(f"📅 Date: {d_str}")
        
        # Table Header
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
            
            # Edit/Delete Buttons
            edit_btn, del_btn = c5.columns(2)
            if edit_btn.button("✏️", key=f"edit_{d_str}_{i}"):
                st.session_state.editing_key = (d_str, i)
                st.rerun()
            if del_btn.button("🗑️", key=f"del_{d_str}_{i}"):
                st.session_state.data_by_date[d_str]["items"].pop(i)
                st.rerun()

            # Prep for Export
            row = item.copy()
            row.update({"Date": d_str, "Tax %": day_data["tax_rate"], "Paid": day_data["payment_received"]})
            export_list.append(row)

        # Day Summary
        tax_val = day_subtotal * (day_data["tax_rate"] / 100)
        day_total = day_subtotal + tax_val
        day_pending = day_total - day_data["payment_received"]
        
        grand_total_billed += day_total
        grand_total_paid += day_data["payment_received"]

        # Financial Summary for the day
        s1, s2, s3, s4 = st.columns(4)
        s1.write(f"**Subtotal:** Rs {day_subtotal:,.2f}")
        s2.write(f"**Tax ({day_data['tax_rate']}%):** Rs {tax_val:,.2f}")
        s3.write(f"**Paid:** Rs {day_data['payment_received']:,.2f}")
        s4.markdown(f"**Pending:** :red[Rs {day_pending:,.2f}]")
        st.divider()

# --- 4. Grand Totals & Export ---
if export_list:
    st.subheader("🏁 Overall Summary (All Dates)")
    g1, g2, g3 = st.columns(3)
    g1.metric("Total Billed", f"Rs {grand_total_billed:,.2f}")
    g2.metric("Total Received", f"Rs {grand_total_paid:,.2f}")
    g3.metric("Total Outstanding", f"Rs {grand_total_billed - grand_total_paid:,.2f}")

    def get_excel_file():
        df = pd.DataFrame(export_list)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Business_Ledger')
        return output.getvalue()

    st.download_button(
        "📥 Download Consolidated Excel Report",
        data=get_excel_file(),
        file_name=f"Ledger_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
else:
    st.info("No entries found. Select a date and add your first product!")
