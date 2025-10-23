import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from st-aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import io

st.set_page_config(page_title="Issue Escalation Tool", layout="wide")
st.title("📊 Issue Pivot & Escalation Email Tool")

# --- File Upload ---
uploaded_file = st.file_uploader("Upload your Jira report (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file:
    # --- Read File ---
    try:
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(io.BytesIO(uploaded_file.read()), encoding_errors="ignore")
    except Exception as e:
        st.error(f"❌ Error reading file: {e}")
        st.stop()

    st.success(f"✅ File uploaded: {uploaded_file.name}")

    # --- Auto-detect datetime fields ---
    helper_cols = []
    for col in df.columns:
        try:
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().any():
                df[col] = parsed
                # hidden helper columns for pivot
                df[f"{col}_Year"] = parsed.dt.year
                df[f"{col}_Month"] = parsed.dt.to_period("M").dt.to_timestamp()
                df[f"{col}_Day"] = parsed.dt.date
                helper_cols.extend([f"{col}_Year", f"{col}_Month", f"{col}_Day"])
        except Exception:
            continue

    # --- Ag-Grid Pivot / Group View ---
    st.subheader("🧮 Pivot Table / Grouped View")

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(enablePivot=True, enableValue=True, enableRowGroup=True,
                                sortable=True, filter=True, resizable=True)
    gb.configure_side_bar()
    gb.configure_selection('multiple', use_checkbox=True)
    gb.configure_pagination(paginationAutoPageSize=True)

    # hide helper columns by default
    for c in helper_cols:
        gb.configure_column(c, hide=True)

    grid_options = gb.build()
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        enable_enterprise_modules=True,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        height=600,
        theme="alpine"
    )

    # --- Get Selected Rows ---
    selected_rows = grid_response['selected_rows']
    if selected_rows:
        selected_df = pd.DataFrame(selected_rows).drop('_selectedRowNodeInfo', axis=1, errors='ignore')
        st.subheader("✅ Selected Rows for Email")
        st.dataframe(selected_df)

        # --- Email Section ---
        st.subheader("✉️ Send Email")
        sender = st.text_input("Sender Email")
        password = st.text_input("Sender Password", type="password")
        recipient = st.text_input("Recipient Email")
        subject = st.text_input("Email Subject", value="Escalation: Selected Issues")

        if st.button("📨 Send Email"):
            try:
                html_table = selected_df.to_html(index=False, border=1)
                msg = MIMEText(html_table, "html")
                msg['Subject'] = subject
                msg['From'] = sender
                msg['To'] = recipient

                # Send email
                with smtplib.SMTP("smtp.office365.com", 587) as server:
                    server.starttls()
                    server.login(sender, password)
                    server.send_message(msg)

                st.success(f"✅ Email sent successfully to {recipient}")
            except Exception as e:
                st.error(f"❌ Failed to send email: {e}")
    else:
        st.info("Select the rows you want to include in the email.")

else:
    st.info("📂 Please upload a Jira report file to get started.")
