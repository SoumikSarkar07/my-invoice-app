import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import date

st.set_page_config(page_title="Multi-Date Product Manager", layout="wide")

st.title("📦 Print-O-Pack")

# Initialize session state for grouping by date
if 'data_by_date' not in st.session_state:
    st.session_state.data_by_date = {}
if 'editing_key' not in st.session_state:
    st.session_state.editing_key = None # (date, index)

# --- 1. Date & Product Entry Section ---
with st.sidebar:
    st.header("📅 Select Date")
    active_date = st.date_input("Working Date", value=date.today())
    active_date_str = active_date.strftime("%Y-%m-%d")

with st.expander(f"📝 Add Product for {active_date_str}", expanded=True):
    # Check if we are editing an existing entry
    edit_info = st.session_state.editing_key
    current_item = None
    if edit_info and edit_info[0] == active_date_str:
        current_item = st.session_state.data_by_date[active_date_str][edit_info[1]]

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        desc = st.text_input("Product Description", value=current_item['Description'] if current_item else "")
    with col2:
        qty = st.number_input("Quantity", min_value=1, step=1, value=current_item['Quantity'] if current_item else 1)
    with col3:
        rate = st.number_input("Rate", min_value=0.0, step=0.01, value=current_item['Rate'] if current_item else 0.0)

    btn_label = "Update Product" if edit_info else "Add to Date"
    if st.button(btn_label, type="primary"):
        if desc:
            new_entry = {"Description": desc, "Quantity": qty, "Rate": rate, "Amount": qty * rate}
            
            if active_date_str not in st.session_state.data_by_date:
                st.session_state.data_by_date[active_date_str] = []
            
            if edit_info:
                st.session_state.data_by_date[active_date_str][edit_info[1]] = new_entry
                st.session_state.editing_key = None
            else:
                st.session_state.data_by_date[active_date_str].append(new_entry)
            st.rerun()

    if edit_info:
        if st.button("Cancel Edit"):
            st.session_state.editing_key = None
            st.rerun()

# --- 2. Data Display & Management ---
if st.session_state.data_by_date:
    all_rows = []
    
    # Flatten the dictionary for display and export
    for d_str, items in sorted(st.session_state.data_by_date.items()):
        st.markdown(f"### 🗓️ Date: {d_str}")
        
        # Display header
        h1, h2, h3, h4, h5 = st.columns([3, 1, 1, 1, 1])
        h1.write("**Description**")
        h2.write("**Qty**")
        h3.write("**Rate**")
        h4.write("**Total**")
        h5.write("**Actions**")

        for i, item in enumerate(items):
            c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
            c1.write(item['Description'])
            c2.write(str(item['Quantity']))
            c3.write(f"Rs {item['Rate']:,.2f}")
            c4.write(f"Rs {item['Amount']:,.2f}")
            
            # Action Buttons
            with c5:
                e_col, d_col = st.columns(2)
                if e_col.button("✏️", key=f"edit_{d_str}_{i}"):
                    st.session_state.editing_key = (d_str, i)
                    st.rerun()
                if d_col.button("🗑️", key=f"del_{d_str}_{i}"):
                    st.session_state.data_by_date[d_str].pop(i)
                    if not st.session_state.data_by_date[d_str]:
                        del st.session_state.data_by_date[d_str]
                    st.rerun()
            
            # Prepare for export dataframe
            export_row = item.copy()
            export_row['Date'] = d_str
            all_rows.append(export_row)
        st.divider()

    # --- 3. Global Totals & Tax ---
    df_main = pd.DataFrame(all_rows)
    subtotal = df_main['Amount'].sum()

    col_tax, col_res = st.columns(2)
    with col_tax:
        tax_perc = st.number_input("Apply Tax to Grand Total (%)", min_value=0.0, step=0.1)
        tax_val = subtotal * (tax_perc / 100)
        grand_total = subtotal + tax_val

    with col_res:
        st.write(f"**Overall Subtotal:** Rs {subtotal:,.2f}")
        st.write(f"**Tax Amount ({tax_perc}%):** Rs {tax_val:,.2f}")
        st.subheader(f"Grand Total: Rs {grand_total:,.2f}")

    # --- 4. Export to Excel ---
    def to_excel(df, sub, t_val, g_total):
        # Sort by date for the Excel sheet
        df = df[['Date', 'Description', 'Quantity', 'Rate', 'Amount']]
        summary = pd.DataFrame([
            {"Date": "", "Description": "SUBTOTAL", "Amount": sub},
            {"Date": "", "Description": f"TAX ({tax_perc}%)", "Amount": t_val},
            {"Date": "", "Description": "GRAND TOTAL", "Amount": g_total}
        ])
        final_df = pd.concat([df, summary], ignore_index=True)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Monthly Export')
        return output.getvalue()

    st.download_button(
        label="📥 Download Consolidated Excel",
        data=to_excel(df_main, subtotal, tax_val, grand_total),
        file_name=f"inventory_report_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
else:
    st.info("Start by selecting a date in the sidebar and adding products.")
