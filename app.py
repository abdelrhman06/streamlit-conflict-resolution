import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime

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

    # طباعة أسماء الأعمدة لمعرفة الأخطاء إن وجدت
    print("Groups Columns:", groups.columns.tolist())

    # تنظيف أسماء الأعمدة
    groups.columns = groups.columns.str.strip()
    physical_sessions.columns = physical_sessions.columns.str.strip()
    
    # البحث عن عمود Grade بشكل ديناميكي
    grade_col = [col for col in groups.columns if "Grade" in col][0]  # يختار العمود الذي يحتوي على "Grade"
    groups["Grade"] = groups[grade_col].str.strip()
    
    # تحويل التواريخ إلى datetime
    physical_sessions["Event Date"] = pd.to_datetime(physical_sessions["Event Date"], errors='coerce')
    physical_sessions["Event Start Date"] = pd.to_datetime(physical_sessions["Event Start Date"], errors='coerce')
    connect_sessions_l1["Event Start Date"] = pd.to_datetime(connect_sessions_l1["Event Start Date"], errors='coerce')
    connect_sessions_l2["Event Start Date"] = pd.to_datetime(connect_sessions_l2["Event Start Date"], errors='coerce')
    groups["Event Start Time"] = pd.to_datetime(groups["Event Start Time"], format="%H:%M:%S", errors='coerce').dt.time
    
    # استخراج اليوم من التواريخ
    physical_sessions["Day"] = physical_sessions["Event Date"].dt.day_name()
    connect_sessions_l1["Day"] = connect_sessions_l1["Event Start Date"].dt.day_name()
    connect_sessions_l2["Day"] = connect_sessions_l2["Event Start Date"].dt.day_name()
    groups["Day"] = groups["Weekday"]

    # دالة لتحويل الوقت مع التحقق من القيم
    def parse_time(value):
        if pd.notna(value):
            value = str(value).strip()
            try:
                return datetime.strptime(value, "%H:%M:%S").time()
            except ValueError:
                return None  # لو لم يكن بتنسيق الوقت الصحيح، يتم إرجاع None
        return None

    # استخراج المستوى واللغة والصف الدراسي
    def extract_session_info(session_code, username, df_groups):
        if isinstance(session_code, str):
            group_info = df_groups[df_groups["Session Code"] == session_code]
            if not group_info.empty:
                level = group_info.iloc[0]["Level"]
                language = group_info.iloc[0].get("Language Type", group_info.iloc[0].get("Language"))
                grade = group_info.iloc[0].get("Grade", "Unknown")
            else:
                level = "Level 2" if session_code[1].isdigit() else "Level 1"
                language = "Arabic" if "A" in session_code else "English"
                grade = "Unknown"

            return level, language, grade
        return None, None, None

    # تطبيق التحليل على الجروبات
    for df in [connect_sessions_l1, connect_sessions_l2]:
        df[["Level", "Language", "Grade"]] = df.apply(
            lambda row: pd.Series(extract_session_info(row["Session Code"], row["Username"], groups)), axis=1
        )

    # إنشاء قائمة النتائج
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
            
            # استخدام الدالة parse_time لضمان تحويل القيم بشكل صحيح
            requested_time = parse_time(row["Requested Time"])
            alternative_time1 = parse_time(row["Alternative Time 1"])
            alternative_time2 = parse_time(row["Alternative Time 2"])

            student_info = connect_sessions[connect_sessions["Username"] == username]

            if not student_info.empty:
                student_row = student_info.iloc[0]
                level, language, grade = student_row["Level"], student_row["Language"], student_row["Grade"]
                old_group = student_row["Session Code"]
                old_group_time = student_row["Event Start Date"].time()
                
                possible_groups = groups[
                    (groups["Level"] == level) &
                    (groups["Language Type"] == language) &
                    (groups["Grade"] == grade) &
                    (groups["Day"] == requested_day)
                ]

                new_group = possible_groups.iloc[0]["Session Code"] if not possible_groups.empty else "No Suitable Group"
                new_group_time = possible_groups.iloc[0]["Event Start Time"] if not possible_groups.empty else None

                session_requests.loc[session_requests["Username"] == username, [
                    "New Group", "New Group Time",
                    "Old Group", "Old Group Time"
                ]] = [
                    new_group, new_group_time,
                    old_group, old_group_time
                ]
                sheets[sheet_name] = pd.concat([sheets[sheet_name], session_requests[session_requests["Username"] == username]], ignore_index=True)

    # حفظ النتائج في ملف Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in sheets.items():
            df.astype(str).to_excel(writer, sheet_name=sheet_name, index=False)
        writer.close()
    output.seek(0)

    # توفير زر لتحميل التقرير
    st.write("✅ تم معالجة البيانات بنجاح. انقر أدناه لتنزيل التقرير.")
    st.download_button(
        label="📥 تنزيل التقرير",
        data=output,
        file_name="session_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
