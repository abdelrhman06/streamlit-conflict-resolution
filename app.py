import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime, timedelta

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

    # استخراج اليوم والوقت
    physical_sessions["Physical Group Day"] = physical_sessions["Event Start Date"].dt.day_name()
    physical_sessions["Physical Group Time"] = physical_sessions["Event Start Date"].dt.time

    # إضافة الأعمدة إلى session_requests
    session_requests_l1 = session_requests_l1.merge(
        physical_sessions[["Username", "Physical Group Time", "Physical Group Day"]], on="Username", how="left"
    )
    session_requests_l2 = session_requests_l2.merge(
        physical_sessions[["Username", "Physical Group Time", "Physical Group Day"]], on="Username", how="left"
    )

    # إنشاء قائمة للنتائج
    sheets = {"Session Requests L1": pd.DataFrame(), "Session Requests L2": pd.DataFrame()}
    group_counts = {}

    for session_requests, sheet_name, connect_sessions in zip(
        [session_requests_l1, session_requests_l2],
        ["Session Requests L1", "Session Requests L2"],
        [connect_sessions_l1, connect_sessions_l2]
    ):
        for _, row in session_requests.iterrows():
            username = row["Username"]
            requested_day = row["Requested Day"]
            requested_time = row["Requested Time"]

            student_info = connect_sessions[connect_sessions["Username"] == username]
            if not student_info.empty:
                student_row = student_info.iloc[0]
                level = student_row.get("Level", "Unknown")
                language = student_row.get("Language", "Unknown")
                grade = student_row.get("Grade", "Unknown")
                old_group = student_row["Session Code"]
                old_group_time = student_row["Event Start Date"].time()

                physical_info = physical_sessions[physical_sessions["Username"] == username]
                physical_group = physical_info["Session Code"].values[0] if not physical_info.empty else None
                physical_group_time = physical_info["Physical Group Time"].values[0] if not physical_info.empty else None
                physical_group_day = physical_info["Physical Group Day"].values[0] if not physical_info.empty else None

                def find_alternative_group(day, time):
                    possible_groups = groups[
                        (groups["Level"] == level) &
                        (groups["Language Type"] == language) &
                        (groups["Grade"].str.contains(grade.split()[-1], na=False)) &
                        (groups["Day"] == day) &
                        (groups["Event Start Time"] == time)
                    ]
                    for _, group in possible_groups.iterrows():
                        session_code = group["Session Code"]
                        if session_code == old_group:
                            continue  # ✅ تجنب اختيار نفس الجروب القديم
                        if session_code not in group_counts:
                            group_counts[session_code] = connect_sessions[connect_sessions["Session Code"] == session_code].shape[0]
                        if 15 < group_counts[session_code] < 35:
                            group_counts[session_code] += 1
                            return session_code, group["Event Start Time"], group_counts[session_code]
                    return None, None, None

                new_group, new_group_time, new_group_count = find_alternative_group(requested_day, requested_time)
                if new_group is None:
                    new_group, new_group_time, new_group_count = "No Suitable Group", None, None

                # التحقق من التعارض بين الجلسة الجديدة والجلسة الفيزيائية
                conflict = "No Conflict"
                if physical_group_time and new_group_time:
                    time_difference = abs(datetime.combine(datetime.today(), new_group_time) -
                                          datetime.combine(datetime.today(), physical_group_time))
                    if time_difference <= timedelta(hours=2.5):
                        conflict = "Conflict"

                session_requests.loc[session_requests["Username"] == username, [
                    "New Group", "New Group Time", "New Group Student Count",
                    "Old Group", "Old Group Time", "Physical Group", "Physical Group Time", "Conflict Status"
                ]] = [
                    new_group, new_group_time, new_group_count,
                    old_group, old_group_time, physical_group, physical_group_time, conflict
                ]
                sheets[sheet_name] = pd.concat([sheets[sheet_name], session_requests[session_requests["Username"] == username]], ignore_index=True)

    # حفظ النتائج في ملف Excel في الذاكرة
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
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