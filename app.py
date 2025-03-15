import streamlit as st
import pandas as pd
import io
import re

# عنوان التطبيق
st.title("\ud83d\udcca نظام حل تعارض الجلسات")
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

    # تحويل تواريخ الجلسات إلى datetime
    physical_sessions["Event Start Date"] = pd.to_datetime(physical_sessions["Event Start Date"])
    connect_sessions_l1["Event Start Date"] = pd.to_datetime(connect_sessions_l1["Event Start Date"])
    connect_sessions_l2["Event Start Date"] = pd.to_datetime(connect_sessions_l2["Event Start Date"])

    # استخراج اليوم من Session Code
    def extract_weekday_from_session_code(session_code):
        if isinstance(session_code, str):
            mapping = {"F": "Friday", "S": "Saturday", "M": "Monday", "T": "Tuesday", 
                       "W": "Wednesday", "Th": "Thursday", "Su": "Sunday"}
            return mapping.get(session_code[:2], "Unknown")
        return "Unknown"

    # تطبيق استخراج اليوم
    physical_sessions["Weekday"] = physical_sessions["Session Code"].apply(extract_weekday_from_session_code)
    physical_sessions["Weekday from Date"] = physical_sessions["Event Start Date"].dt.day_name()

    # التحقق من التعارض
    def check_conflict(new_session_time, new_session_day, physical_session_time, physical_session_day):
        time_diff = abs((new_session_time - physical_session_time).total_seconds()) / 3600  # تحويل الفرق إلى ساعات
        return new_session_day == physical_session_day and time_diff < 2.5

    # البحث عن التعارضات
    conflicts = []
    for df in [connect_sessions_l1, connect_sessions_l2]:
        for _, row in df.iterrows():
            username = row["Username"]
            new_session_time = row["Event Start Date"]
            new_session_day = new_session_time.day_name()

            physical_info = physical_sessions[physical_sessions["Username"] == username]
            if not physical_info.empty:
                physical_session_time = physical_info["Event Start Date"].values[0]
                physical_session_day = physical_info["Weekday from Date"].values[0]

                if check_conflict(new_session_time, new_session_day, pd.Timestamp(physical_session_time), physical_session_day):
                    conflicts.append((username, new_session_day, new_session_time, physical_session_day, physical_session_time))

    # تحويل النتائج إلى DataFrame
    conflict_df = pd.DataFrame(conflicts, columns=["Username", "New Session Day", "New Session Time", "Physical Session Day", "Physical Session Time"])

    # حفظ النتائج في ملف Excel في الذاكرة
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        session_requests_l1.to_excel(writer, sheet_name="Session Requests L1", index=False)
        session_requests_l2.to_excel(writer, sheet_name="Session Requests L2", index=False)
        writer.close()
        processed_data = output.getvalue()
    # عرض زر لتحميل التقرير
    st.write("\u2705 تم معالجة البيانات بنجاح. انقر أدناه لتنزيل التقرير.")
    st.download_button(
        label="\ud83d\udcbd تنزيل التقرير",
        data=processed_data,
        file_name="session_conflicts_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
