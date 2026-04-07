import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Product Manager", layout="wide")

st.title("📦 Product Manager & Exporter")

# Initialize session state
if 'product_list' not in st.session_state:
    st.session_state.product_list = []
if 'editing_index' not in st.session_state:
    st.session_state.editing_index = None

# --- 1. Entry/Edit Form ---
with st.expander("📝 Product Details", expanded=True):
    # Determine if we are editing or adding new
    idx = st.session_state.editing_index
    current_item = st.session_state.product_list[idx] if idx is not None else None

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        desc = st.text_input("Product Description", value=current_item['Description'] if current_item else "")
    with col2:
        qty = st.number_input("Quantity", min_value=1, step=1, value=current_item['Quantity'] if current_item else 1)
    with col3:
        rate = st.number_input("Rate", min_value=0.0, step=0.01, value=current_item['Rate'] if current_item else 0.0)

    btn_label = "Update Product" if idx is not None else "Add to List"
    if st.button(btn_label, type="primary"):
        if desc:
            new_data = {"Description": desc, "Quantity": qty, "Rate": rate, "Amount": qty * rate}
            if idx is not None:
                st.session_state.product_list[idx] = new_data
                st.session_state.editing_index = None # Reset editing mode
            else:
                st.session_state.product_list.append(new_data)
            st.rerun()
        else:
            st.error("Description is required")

    if idx is not None:
        if st.button("Cancel Edit"):
            st.session_state.editing_index = None
            st.rerun()

# --- 2. Management Table ---
if st.session_state.product_list:
    st.subheader("Manage Entries")
    
    # Create header row
    h1, h2, h3, h4, h5 = st.columns([3, 1, 1, 1, 1])
    h1.write("**Description**")
    h2.write("**Qty**")
    h3.write("**Rate**")
    h4.write("**Total**")
    h5.write("**Actions**")

    # Display items with Edit/Delete buttons
    for i, item in enumerate(st.session_state.product_list):
        c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
        c1.write(item['Description'])
        c2.write(str(item['Quantity']))
        c3.write(f"Rs {item['Rate']:,.2f}")
        c4.write(f"Rs {item['Amount']:,.2f}")
        
        # Action buttons
        with c5:
            edit_col, del_col = st.columns(2)
            if edit_col.button("✏️", key=f"edit_{i}"):
                st.session_state.editing_index = i
                st.rerun()
            if del_col.button("🗑️", key=f"del_{i}"):
                st.session_state.product_list.pop(i)
                st.rerun()

    # --- 3. Totals & Tax ---
    st.divider()
    df = pd.DataFrame(st.session_state.product_list)
    subtotal = df['Amount'].sum()
    
    col_a, col_b = st.columns(2)
    with col_a:
        tax_perc = st.number_input("Grand Total Tax (%)", min_value=0.0, step=0.1, value=0.0)
        tax_val = subtotal * (tax_perc / 100)
        grand_total = subtotal + tax_val
    
    with col_b:
        st.write(f"**Subtotal:** Rs {subtotal:,.2f}")
        st.write(f"**Tax Amount:** Rs {tax_val:,.2f}")
        st.markdown(f"### Grand Total: Rs {grand_total:,.2f}")

    # --- 4. Export ---
    summary_data = [
        {"Description": "SUBTOTAL", "Amount": subtotal},
        {"Description": f"TAX ({tax_perc}%)", "Amount": tax_val},
        {"Description": "GRAND TOTAL", "Amount": grand_total},
    ]
    df_export = pd.concat([df, pd.DataFrame(summary_data)], ignore_index=True)

    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Invoice')
        return output.getvalue()

    st.download_button(
        label="📥 Export to Excel",
        data=to_excel(df_export),
        file_name="invoice.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
else:
    st.info("List is empty. Use the form above to add products.")
