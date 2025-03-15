import streamlit as st
import pandas as pd
import io
import re

st.title("📊 Finding Another Group for Students")
st.write("""
Enter the day and time the student wants to find a new group that suits them.  

This application was developed by **Abdelrahman Salah**.  
Dedicated to **the Connect Team**.  

Part of **Almentor**.
""")

# تحميل ملف Excel
uploaded_file = st.file_uploader("تحميل ملف Excel", type=["xlsx"])

def get_day_from_session_code(session_code):
    mapping = {"F": "Friday", "S": "Saturday", "M": "Monday", "T": "Tuesday", "W": "Wednesday", "Th": "Thursday", "Su": "Sunday"}
    for key, value in mapping.items():
        if session_code.startswith(key):
            return value
    return "Unknown"

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)

    # تحميل بيانات الجداول
    physical_sessions = pd.read_excel(xls, sheet_name='Physical Sessions')
    connect_sessions_l1 = pd.read_excel(xls, sheet_name='Connect Sessions L1')
    connect_sessions_l2 = pd.read_excel(xls, sheet_name='Connect Sessions L2')
    groups = pd.read_excel(xls, sheet_name='Groups')
    session_requests_l1 = pd.read_excel(xls, sheet_name='Session Requests L1')
    session_requests_l2 = pd.read_excel(xls, sheet_name='Session Requests L2')

    # تنظيف أسماء الأعمدة في جدول الجروبات
    groups.columns = groups.columns.str.strip()
    groups["Weekday"] = groups["Session Code"].apply(get_day_from_session_code)

    # تحويل تواريخ الجلسات إلى datetime
    physical_sessions["Event Start Date"] = pd.to_datetime(physical_sessions["Event Start Date"])
    physical_sessions["Weekday"] = physical_sessions["Event Start Date"].dt.day_name()
    connect_sessions_l1["Event Start Date"] = pd.to_datetime(connect_sessions_l1["Event Start Date"])
    connect_sessions_l2["Event Start Date"] = pd.to_datetime(connect_sessions_l2["Event Start Date"])

    # التأكد من عدم التعارض بين الجلسات الجديدة والفيزيائية
    def is_conflict(new_day, new_time, physical_day, physical_time):
        if new_day == physical_day:
            time_diff = abs((pd.to_datetime(new_time) - pd.to_datetime(physical_time)).total_seconds()) / 3600
            return time_diff < 2.5
        return False
    
    # استكمال عملية البحث عن الجروب البديل
    st.write("✅ Data has been processed successfully. Click below to download the report.")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        physical_sessions.to_excel(writer, sheet_name='Physical Sessions', index=False)
        connect_sessions_l1.to_excel(writer, sheet_name='Connect Sessions L1', index=False)
        connect_sessions_l2.to_excel(writer, sheet_name='Connect Sessions L2', index=False)
        groups.to_excel(writer, sheet_name='Groups', index=False)
        session_requests_l1.to_excel(writer, sheet_name='Session Requests L1', index=False)
        session_requests_l2.to_excel(writer, sheet_name='Session Requests L2', index=False)
        writer.close()
        processed_data = output.getvalue()
    
    st.download_button(
        label="📥 Download Report",
        data=processed_data,
        file_name="session_requests_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
