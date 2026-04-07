import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO
from datetime import date

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('ledger.db')
    c = conn.cursor()
    # Table for individual products
    c.execute('''CREATE TABLE IF NOT EXISTS items 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date TEXT, description TEXT, quantity INTEGER, rate REAL, amount REAL)''')
    # Table for daily financial settings (tax and payments)
    c.execute('''CREATE TABLE IF NOT EXISTS daily_finance 
                 (date TEXT PRIMARY KEY, tax_rate REAL, payment_received REAL)''')
    conn.commit()
    conn.close()

def run_query(query, params=(), fetch=False):
    conn = sqlite3.connect('ledger.db')
    c = conn.cursor()
    c.execute(query, params)
    data = None
    if fetch:
        data = c.fetchall()
    conn.commit()
    conn.close()
    return data

init_db()

st.set_page_config(page_title="Database Ledger", layout="wide")
st.title("🗄️ Persistent Business Ledger")
st.write("Data is saved to `ledger.db` and persists across sessions.")

# --- Session State for Editing ---
if 'editing_id' not in st.session_state:
    st.session_state.editing_id = None

# --- 1. Sidebar: Date & Financial Settings ---
with st.sidebar:
    st.header("📅 Entry Settings")
    active_date = st.date_input("Select Working Date", value=date.today())
    active_date_str = active_date.strftime("%Y-%m-%d")
    
    # Fetch existing finance data for this date
    finance_data = run_query("SELECT tax_rate, payment_received FROM daily_finance WHERE date=?", (active_date_str,), fetch=True)
    
    if not finance_data:
        run_query("INSERT INTO daily_finance (date, tax_rate, payment_received) VALUES (?, ?, ?)", (active_date_str, 0.0, 0.0))
        tax_rate, pay_received = 0.0, 0.0
    else:
        tax_rate, pay_received = finance_data[0]

    st.divider()
    st.subheader(f"Financials: {active_date_str}")
    
    new_tax = st.number_input("Tax Rate (%)", min_value=0.0, step=0.1, value=tax_rate)
    new_pay = st.number_input("Payment Received (Rs )", min_value=0.0, step=1.0, value=pay_received)
    
    if st.button("💾 Save Date Settings"):
        run_query("UPDATE daily_finance SET tax_rate=?, payment_received=? WHERE date=?", (new_tax, new_pay, active_date_str))
        st.success("Settings Saved!")
        st.rerun()

# --- 2. Input Form (Add / Update) ---
edit_id = st.session_state.editing_id
current_item = None
if edit_id:
    res = run_query("SELECT description, quantity, rate FROM items WHERE id=?", (edit_id,), fetch=True)
    if res: current_item = res[0]

with st.expander("📝 Add / Edit Product Details", expanded=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        desc = st.text_input("Product Description", value=current_item[0] if current_item else "")
    with c2:
        qty = st.number_input("Quantity", min_value=1, value=current_item[1] if current_item else 1)
    with c3:
        rate = st.number_input("Rate (Rs )", min_value=0.0, value=current_item[2] if current_item else 0.0)

    btn_col1, btn_col2 = st.columns([1, 5])
    if btn_col1.button("Update" if edit_id else "Add Item", type="primary"):
        if desc:
            amount = qty * rate
            if edit_id:
                run_query("UPDATE items SET description=?, quantity=?, rate=?, amount=? WHERE id=?", (desc, qty, rate, amount, edit_id))
                st.session_state.editing_id = None
            else:
                run_query("INSERT INTO items (date, description, quantity, rate, amount) VALUES (?, ?, ?, ?, ?)", (active_date_str, desc, qty, rate, amount))
            st.rerun()
    
    if edit_id and btn_col2.button("Cancel Edit"):
        st.session_state.editing_id = None
        st.rerun()

# --- 3. Data Display & Calculations ---
st.divider()
all_items = run_query("SELECT id, date, description, quantity, rate, amount FROM items ORDER BY date DESC", fetch=True)
finance_map = {row[0]: (row[1], row[2]) for row in run_query("SELECT date, tax_rate, payment_received FROM daily_finance", fetch=True)}

grand_total_billed, grand_total_paid = 0, 0
export_ledger, export_dues = [], []

if all_items:
    df_all = pd.DataFrame(all_items, columns=['id', 'date', 'description', 'quantity', 'rate', 'amount'])
    
    for d_str in df_all['date'].unique():
        day_df = df_all[df_all['date'] == d_str]
        day_tax_rate, day_paid = finance_map.get(d_str, (0.0, 0.0))
        
        st.subheader(f"🗓️ Date: {d_str}")
        h1, h2, h3, h4, h5 = st.columns([3, 1, 1, 1, 1.5])
        h1.write("**Item**"); h2.write("**Qty**"); h3.write("**Rate**"); h4.write("**Total**"); h5.write("**Actions**")

        day_subtotal = 0
        for _, row in day_df.iterrows():
            day_subtotal += row['amount']
            c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1.5])
            c1.write(row['description'])
            c2.write(str(row['quantity']))
            c3.write(f"Rs {row['rate']:,.2f}")
            c4.write(f"Rs {row['amount']:,.2f}")
            
            e_btn, d_btn = c5.columns(2)
            if e_btn.button("✏️", key=f"e_{row['id']}"):
                st.session_state.editing_id = row['id']
                st.rerun()
            if d_btn.button("🗑️", key=f"d_{row['id']}"):
                run_query("DELETE FROM items WHERE id=?", (row['id'],))
                st.rerun()

            export_ledger.append({"Date": d_str, "Item": row['description'], "Qty": row['quantity'], "Rate": row['rate'], "Total": row['amount']})

        tax_val = day_subtotal * (day_tax_rate / 100)
        day_total = day_subtotal + tax_val
        grand_total_billed += day_total
        grand_total_paid += day_paid
        
        export_dues.append({"Date": d_str, "Subtotal": day_subtotal, "Tax %": day_tax_rate, "Total Billed": day_total, "Paid": day_paid, "Pending": day_total - day_paid})

        s1, s2, s3, s4 = st.columns(4)
        s1.write(f"**Subtotal:** Rs {day_subtotal:,.2f}")
        s2.write(f"**Tax ({day_tax_rate}%):** Rs {tax_val:,.2f}")
        s3.write(f"**Paid:** Rs {day_paid:,.2f}")
        s4.markdown(f"**Pending:** :red[Rs {day_total - day_paid:,.2f}]")
        st.divider()

# --- 4. Totals & Multi-Sheet Export ---
if export_ledger:
    st.subheader("🏁 Grand Summary")
    g1, g2, g3 = st.columns(3)
    g1.metric("Total Billed", f"Rs {grand_total_billed:,.2f}")
    g2.metric("Total Received", f"Rs {grand_total_paid:,.2f}")
    g3.metric("Outstanding", f"Rs {grand_total_billed - grand_total_paid:,.2f}")

    def to_excel():
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pd.DataFrame(export_ledger).to_excel(writer, index=False, sheet_name='Itemized_Ledger')
            pd.DataFrame(export_dues).to_excel(writer, index=False, sheet_name='Dues_Summary')
        return output.getvalue()

    st.download_button("📥 Download Excel Report", data=to_excel(), file_name=f"Ledger_{date.today()}.xlsx", use_container_width=True)
