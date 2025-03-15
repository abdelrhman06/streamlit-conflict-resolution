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

    # تحويل تواريخ الجلسات إلى datetime
    physical_sessions["Event Start Date"] = pd.to_datetime(physical_sessions["Event Start Date"])
    connect_sessions_l1["Event Start Date"] = pd.to_datetime(connect_sessions_l1["Event Start Date"])
    connect_sessions_l2["Event Start Date"] = pd.to_datetime(connect_sessions_l2["Event Start Date"])

    # استخراج اليوم من Session Code
    def extract_weekday_from_session_code(session_code):
        if isinstance(session_code, str):
            if session_code.startswith("F"): return "Friday"
            if session_code.startswith("S"): return "Saturday"
            if session_code.startswith("M"): return "Monday"
            if session_code.startswith("T"): return "Tuesday"
            if session_code.startswith("W"): return "Wednesday"
            if session_code.startswith("Th"): return "Thursday"
            if session_code.startswith("Su"): return "Sunday"
        return "Unknown"

    # إضافة عمود Weekday بناءً على Session Code في Physical Sessions
    physical_sessions["Weekday"] = physical_sessions["Session Code"].apply(extract_weekday_from_session_code)
    physical_sessions["Weekday from Date"] = physical_sessions["Event Start Date"].dt.day_name()

    # دالة التحقق من التعارض
    def check_conflict(new_session_time, new_session_day, physical_session_time, physical_session_day):
        time_diff = abs((new_session_time - physical_session_time).total_seconds()) / 3600  # تحويل الفرق إلى ساعات
        if new_session_day == physical_session_day and time_diff < 2.5:
            return True  # يوجد تعارض
        return False  # لا يوجد تعارض

    # البحث عن التعارض بين الجلسات الـ Connect والجلسات الـ Physical
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

    # حفظ البيانات إلى ملف Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        conflict_df.to_excel(writer, sheet_name="Conflicts", index=False)
        writer.close()
        processed_data = output.getvalue()

    # عرض زر لتحميل التقرير
    st.write("✅ تم معالجة البيانات بنجاح. انقر أدناه لتنزيل التقرير.")
    st.download_button(
        label="📥 تنزيل التقرير",
        data=processed_data,
        file_name="session_conflicts_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
