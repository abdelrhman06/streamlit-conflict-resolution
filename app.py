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

# 📂 تحميل ملف Excel
uploaded_file = st.file_uploader("📂 Upload an Excel file", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)

    # 📖 تحميل بيانات الجداول
    physical_sessions = pd.read_excel(xls, sheet_name='Physical Sessions')
    connect_sessions_l1 = pd.read_excel(xls, sheet_name='Connect Sessions L1')
    connect_sessions_l2 = pd.read_excel(xls, sheet_name='Connect Sessions L2')
    groups = pd.read_excel(xls, sheet_name='Groups')
    session_requests_l1 = pd.read_excel(xls, sheet_name='Session Requests L1')
    session_requests_l2 = pd.read_excel(xls, sheet_name='Session Requests L2')

    # 🧹 تنظيف أسماء الأعمدة
    groups.columns = groups.columns.str.strip()
    physical_sessions.columns = physical_sessions.columns.str.strip()

    # 📅 تحويل التواريخ
    physical_sessions["Event Start Date"] = pd.to_datetime(physical_sessions["Event Start Date"], errors='coerce')
    connect_sessions_l1["Event Start Date"] = pd.to_datetime(connect_sessions_l1["Event Start Date"], errors='coerce')
    connect_sessions_l2["Event Start Date"] = pd.to_datetime(connect_sessions_l2["Event Start Date"], errors='coerce')

    # 🔹 دالة استخراج اليوم من Session Code
    def get_day_from_session_code(session_code):
        if isinstance(session_code, str):
            if "F" in session_code:
                return "Friday"
            elif "S" in session_code:
                return "Saturday"
            elif "M" in session_code:
                return "Monday"
            elif "T" in session_code:
                return "Tuesday"
            elif "W" in session_code:
                return "Wednesday"
            elif "Th" in session_code:
                return "Thursday"
            elif "Su" in session_code:
                return "Sunday"
        return "Unknown"

    # 📌 استخراج اليوم من `Event Start Date` في `Physical Sessions`
    physical_sessions["Weekday"] = physical_sessions["Event Start Date"].dt.day_name()

    # 📝 إضافة اليوم إلى جدول الجروبات
    groups["Weekday"] = groups["Session Code"].astype(str).apply(get_day_from_session_code)

    # 📌 تطبيق استخراج اليوم في `Connect Sessions`
    for df in [connect_sessions_l1, connect_sessions_l2]:
        df["Weekday"] = df["Session Code"].astype(str).apply(get_day_from_session_code)

    # 🔍 دالة لحساب فرق الساعات بين جلستين
    def time_difference(time1, time2):
        return abs((pd.Timestamp.combine(pd.Timestamp.today(), time1) - pd.Timestamp.combine(pd.Timestamp.today(), time2)).total_seconds() / 3600)

    # 📊 إنشاء قائمة للنتائج
    sheets = {"Session Requests L1": pd.DataFrame(), "Session Requests L2": pd.DataFrame()}
    group_counts = {}

    for session_requests, sheet_name, connect_sessions in zip(
        [session_requests_l1, session_requests_l2],
        ["Session Requests L1", "Session Requests L2"],
        [connect_sessions_l1, connect_sessions_l2]
    ):
        session_requests = session_requests.copy()
        for _, row in session_requests.iterrows():
            username = row["Username"]
            requested_day = row["Requested Day"]
            requested_time = row["Requested Time"]
            alternative_time1 = row["Alternative Time 1"]
            alternative_time2 = row["Alternative Time 2"]

            student_info = connect_sessions[connect_sessions["Username"] == username]

            if not student_info.empty:
                student_row = student_info.iloc[0]
                level, language, grade = student_row["Level"], student_row["Language"], student_row["Grade"]
                old_group = student_row["Session Code"]
                old_group_time = student_row["Event Start Date"].time()
                old_group_day = student_row["Weekday"]
                physical_info = physical_sessions[physical_sessions["Username"] == username]
                physical_group = physical_info["Session Code"].values[0] if not physical_info.empty else None
                physical_group_time = physical_info["Event Start Date"].dt.time.values[0] if not physical_info.empty else None
                physical_group_day = physical_info["Weekday"].values[0] if not physical_info.empty else None

                # 🏷️ البحث عن بديل مناسب مع التحقق من عدم التعارض
                def find_alternative_group(day, time):
                    if day is None or time is None:
                        return None, None, None

                    possible_groups = groups[
                        (groups["Level"] == level) &
                        (groups["Language Type"] == language) &
                        (groups["Grade"].str.contains(grade.split()[-1], na=False)) &
                        (groups["Weekday"] == day) &
                        (groups["Event Start Time"] == time)
                    ]
                    for _, group in possible_groups.iterrows():
                        session_code = group["Session Code"]
                        if session_code == old_group:
                            continue
                        if session_code not in group_counts:
                            group_counts[session_code] = connect_sessions[connect_sessions["Session Code"] == session_code].shape[0]
                        if 15 < group_counts[session_code] < 35:
                            new_group_time = group["Event Start Time"]
                            new_group_day = group["Weekday"]

                            # ✅ التحقق من التعارض
                            if physical_group_time and physical_group_day:
                                if new_group_day == physical_group_day and time_difference(new_group_time, physical_group_time) < 2.5:
                                    continue  # ❌ يعتبر تعارض، يبحث عن مجموعة أخرى

                            group_counts[session_code] += 1
                            return session_code, new_group_time, group_counts[session_code]
                    return None, None, None

                # 🔁 البحث عن جلسة جديدة مناسبة بدون تعارض
                new_group, new_group_time, new_group_count = find_alternative_group(requested_day, requested_time)
                if new_group is None:
                    new_group, new_group_time, new_group_count = find_alternative_group(requested_day, alternative_time1)
                if new_group is None:
                    new_group, new_group_time, new_group_count = find_alternative_group(requested_day, alternative_time2)
                if new_group is None:
                    new_group, new_group_time, new_group_count = "No Suitable Group", None, None

                session_requests.loc[session_requests["Username"] == username, [
                    "New Group", "New Group Time", "New Group Student Count",
                    "Old Group", "Old Group Time", "Physical Group", "Physical Group Time"
                ]] = [
                    new_group, new_group_time, new_group_count,
                    old_group, old_group_time, physical_group, physical_group_time
                ]
                sheets[sheet_name] = pd.concat([sheets[sheet_name], session_requests[session_requests["Username"] == username]], ignore_index=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        writer.close()
        processed_data = output.getvalue()

    st.download_button("📥 Download Report", processed_data, "session_requests_report.xlsx")
