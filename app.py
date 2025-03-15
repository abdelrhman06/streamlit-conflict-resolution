import streamlit as st
import pandas as pd
import io
import re

# عنوان التطبيق
st.title("📊 نظام حل تعارض الجلسات")
st.write("قم بتحميل ملف Excel الخاص بك للحصول على تقرير تعارض الجلسات.")

# تحميل ملف Excel
uploaded_file = st.file_uploader("تحميل ملف Excel", type=["xlsx"])

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
    physical_sessions.columns = physical_sessions.columns.str.strip()

    # تحويل تواريخ الجلسات إلى datetime
    physical_sessions["Event Date"] = pd.to_datetime(physical_sessions["Event Date"])
    physical_sessions["Event Start Date"] = pd.to_datetime(physical_sessions["Event Start Date"])
    connect_sessions_l1["Event Start Date"] = pd.to_datetime(connect_sessions_l1["Event Start Date"])
    connect_sessions_l2["Event Start Date"] = pd.to_datetime(connect_sessions_l2["Event Start Date"])

    # استخراج اليوم من التواريخ
    physical_sessions["Day"] = physical_sessions["Event Date"].dt.day_name()
    physical_sessions["Physical Day"] = physical_sessions["Event Start Date"].dt.day_name()
    connect_sessions_l1["Day"] = connect_sessions_l1["Event Start Date"].dt.day_name()
    connect_sessions_l2["Day"] = connect_sessions_l2["Event Start Date"].dt.day_name()
    groups["Day"] = groups["Weekday"]

    # إضافة اليوم إلى session_requests
    session_requests_l1 = session_requests_l1.merge(
        physical_sessions[["Username", "Physical Day", "Day"]], on="Username", how="left"
    )
    session_requests_l2 = session_requests_l2.merge(
        physical_sessions[["Username", "Physical Day", "Day"]], on="Username", how="left"
    )

    # تجهيز ملف الإخراج
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        physical_sessions.to_excel(writer, sheet_name="Physical Sessions", index=False)
        connect_sessions_l1.to_excel(writer, sheet_name="Connect Sessions L1", index=False)
        connect_sessions_l2.to_excel(writer, sheet_name="Connect Sessions L2", index=False)
        groups.to_excel(writer, sheet_name="Groups", index=False)
        session_requests_l1.to_excel(writer, sheet_name="Session Requests L1", index=False)
        session_requests_l2.to_excel(writer, sheet_name="Session Requests L2", index=False)
        writer.close()
        processed_data = output.getvalue()

    # توفير زر لتحميل التقرير
    st.write("✅ تم معالجة البيانات بنجاح. انقر أدناه لتنزيل التقرير.")
    st.download_button(
        label="📥 تنزيل التقرير",
        data=processed_data,
        file_name="session_requests_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
