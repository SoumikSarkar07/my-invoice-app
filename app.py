import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO
from datetime import date

# --- Database Core Logic ---
def init_db():
    conn = sqlite3.connect('ledger.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date TEXT, description TEXT, quantity INTEGER, rate REAL, amount REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_finance 
                 (date TEXT PRIMARY KEY, tax_rate REAL, payment_received REAL)''')
    conn.commit()
    conn.close()

def run_query(query, params=(), fetch=False):
    conn = sqlite3.connect('ledger.db')
    c = conn.cursor()
    c.execute(query, params)
    data = c.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return data

init_db()

st.set_page_config(page_title="Ledger with Reset", layout="wide")
st.title("🗄️ Business Ledger & Session Manager")

# --- Session State for UI Flow ---
if 'editing_id' not in st.session_state:
    st.session_state.editing_id = None

# --- 1. Sidebar: Date & Financial Controls ---
with st.sidebar:
    st.header("📅 Date Settings")
    active_date = st.date_input("Working Date", value=date.today())
    active_date_str = active_date.strftime("%Y-%m-%d")
    
    # Load or Create financial defaults for the selected date
    finance = run_query("SELECT tax_rate, payment_received FROM daily_finance WHERE date=?", (active_date_str,), fetch=True)
    if not finance:
        run_query("INSERT INTO daily_finance (date, tax_rate, payment_received) VALUES (?, ?, ?)", (active_date_str, 0.0, 0.0))
        tax_rate, pay_received = 0.0, 0.0
    else:
        tax_rate, pay_received = finance[0]

    st.divider()
    st.subheader(f"Ledger for {active_date_str}")
    new_tax = st.number_input("Tax Rate (%)", min_value=0.0, step=0.1, value=tax_rate)
    new_pay = st.number_input("Payment Received (Rs )", min_value=0.0, step=1.0, value=pay_received)
    
    if st.button("💾 Save Date Settings"):
        run_query("UPDATE daily_finance SET tax_rate=?, payment_received=? WHERE date=?", (new_tax, new_pay, active_date_str))
        st.success("Financials Updated!")
        st.rerun()

# --- 2. Input Form (Add/Edit) ---
edit_id = st.session_state.editing_id
current_item = None
if edit_id:
    res = run_query("SELECT description, quantity, rate FROM items WHERE id=?", (edit_id,), fetch=True)
    if res: current_item = res[0]

with st.expander("📝 Product Entry Form", expanded=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        desc = st.text_input("Product Name", value=current_item[0] if current_item else "")
    with c2:
        qty = st.number_input("Qty", min_value=1, value=current_item[1] if current_item else 1)
    with c3:
        rate = st.number_input("Rate (Rs )", min_value=0.0, value=current_item[2] if current_item else 0.0)

    if st.button("Update Item" if edit_id else "Add to Ledger", type="primary"):
        if desc:
            amt = qty * rate
            if edit_id:
                run_query("UPDATE items SET description=?, quantity=?, rate=?, amount=? WHERE id=?", (desc, qty, rate, amt, edit_id))
                st.session_state.editing_id = None
            else:
                run_query("INSERT INTO items (date, description, quantity, rate, amount) VALUES (?, ?, ?, ?, ?)", (active_date_str, desc, qty, rate, amt))
            st.rerun()

# --- 3. Data Processing & Rendering ---
st.divider()
all_data = run_query("SELECT id, date, description, quantity, rate, amount FROM items ORDER BY date DESC", fetch=True)
f_rows = run_query("SELECT date, tax_rate, payment_received FROM daily_finance", fetch=True)
f_map = {r[0]: (r[1], r[2]) for r in f_rows}

export_ledger, export_dues = [], []
total_billed, total_paid = 0, 0

if all_data:
    df = pd.DataFrame(all_data, columns=['id', 'date', 'desc', 'qty', 'rate', 'amt'])
    for d_str in sorted(df['date'].unique(), reverse=True):
        day_df = df[df['date'] == d_str]
        d_tax, d_paid = f_map.get(d_str, (0.0, 0.0))
        
        st.subheader(f"🗓️ {d_str}")
        subtotal = 0
        for _, row in day_df.iterrows():
            subtotal += row['amt']
            cols = st.columns([3, 1, 1, 1, 1.5])
            cols[0].write(row['desc'])
            cols[1].write(f"x{row['qty']}")
            cols[2].write(f"Rs {row['rate']:,.2f}")
            cols[3].write(f"Rs {row['amt']:,.2f}")
            
            e_col, d_col = cols[4].columns(2)
            if e_col.button("✏️", key=f"e_{row['id']}"):
                st.session_state.editing_id = row['id']; st.rerun()
            if d_col.button("🗑️", key=f"d_{row['id']}"):
                run_query("DELETE FROM items WHERE id=?", (row['id'],)); st.rerun()

            export_ledger.append({"Date": d_str, "Item": row['desc'], "Qty": row['qty'], "Rate": row['rate'], "Total": row['amt']})

        # Totals logic
        t_amt = subtotal * (d_tax / 100)
        day_total = subtotal + t_amt
        total_billed += day_total
        total_paid += d_paid
        export_dues.append({"Date": d_str, "Total": day_total, "Paid": d_paid, "Due": day_total - d_paid})
        
        st.info(f"Subtotal: Rs {subtotal:,.2f} | Tax: Rs {t_amt:,.2f} | Due: Rs {day_total - d_paid:,.2f}")
        st.divider()

# --- 4. Export & Clear Functionality ---
if export_ledger:
    st.subheader("🏁 Overall Summary")
    st.metric("Balance Due", f"Rs {total_billed - total_paid:,.2f}")

    # Excel Generation
    def make_excel():
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            pd.DataFrame(export_ledger).to_excel(writer, index=False, sheet_name='Ledger')
            pd.DataFrame(export_dues).to_excel(writer, index=False, sheet_name='Dues')
        return out.getvalue()

    st.download_button("📥 Download Final Excel Report", data=make_excel(), file_name=f"Report_{date.today()}.xlsx", use_container_width=True)

    # CLEAR SESSION BUTTON
    st.warning("Danger Zone: This will permanently delete all records from the database.")
    if st.button("🗑️ Clear All Session Data", type="secondary", use_container_width=True):
        run_query("DELETE FROM items")
        run_query("DELETE FROM daily_finance")
        st.session_state.editing_id = None
        st.success("Database cleared successfully!")
        st.rerun()
