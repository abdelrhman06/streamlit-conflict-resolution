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

    # تنظيف أسماء الأعمدة
    groups.columns = groups.columns.str.strip()
    physical_sessions.columns = physical_sessions.columns.str.strip()
    
    # تحويل التواريخ إلى datetime
    physical_sessions["Event Date"] = pd.to_datetime(physical_sessions["Event Date"])
    physical_sessions["Event Start Date"] = pd.to_datetime(physical_sessions["Event Start Date"])
    connect_sessions_l1["Event Start Date"] = pd.to_datetime(connect_sessions_l1["Event Start Date"])
    connect_sessions_l2["Event Start Date"] = pd.to_datetime(connect_sessions_l2["Event Start Date"])
    
    # استخراج اليوم من التواريخ
    physical_sessions["Day"] = physical_sessions["Event Date"].dt.day_name()
    connect_sessions_l1["Day"] = connect_sessions_l1["Event Start Date"].dt.day_name()
    connect_sessions_l2["Day"] = connect_sessions_l2["Event Start Date"].dt.day_name()
    groups["Day"] = groups["Weekday"]

    # استخراج المستوى واللغة والصف الدراسي
    def extract_session_info(session_code, username, df_groups):
        if isinstance(session_code, str):
            group_info = df_groups[df_groups["Session Code"] == session_code]
            if not group_info.empty:
                level = group_info.iloc[0]["Level"]
                language = group_info.iloc[0].get("Language Type", group_info.iloc[0].get("Language"))
                grade = group_info.iloc[0].get("Grade ", group_info.iloc[0].get("Grade"))
            else:
                level = "Level 2" if session_code[1].isdigit() else "Level 1"
                language = "Arabic" if "A" in session_code else "English"
                grade = None

            if grade is None:
                grade_match = re.search(r"G(\d+)", username)
                grade = f"Grade {grade_match.group(1)}" if grade_match else "Unknown"

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
            requested_time = row["Requested Time"]
            alternative_time1 = row["Alternative Time 1"]
            alternative_time2 = row["Alternative Time 2"]

            student_info = connect_sessions[connect_sessions["Username"] == username]

            if not student_info.empty:
                student_row = student_info.iloc[0]
                level, language, grade = student_row["Level"], student_row["Language"], student_row["Grade"]
                old_group = student_row["Session Code"]
                old_group_time = student_row["Event Start Date"].time()
                
                physical_info = physical_sessions[physical_sessions["Username"] == username]
                if not physical_info.empty:
                    physical_group = physical_info["Session Code"].values[0]
                    physical_group_time = physical_info["Event Start Date"].values[0]
                    physical_group_day = physical_info["Event Date"].dt.day_name().values[0]
                else:
                    physical_group = None
                    physical_group_time = None
                    physical_group_day = None

                session_requests.loc[session_requests["Username"] == username, [
                    "New Group", "New Group Time", "New Group Student Count",
                    "Old Group", "Old Group Time", "Physical Group", "Physical Group Time", "Physical Group Day"
                ]] = [
                    "No Suitable Group", None, None,
                    old_group, old_group_time, physical_group, physical_group_time, physical_group_day
                ]
                sheets[sheet_name] = pd.concat([sheets[sheet_name], session_requests[session_requests["Username"] == username]], ignore_index=True)

    # حفظ النتائج في ملف Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        writer.close()
        processed_data = output.getvalue()

    # توفير زر لتحميل التقرير
    st.write("\u2705 تم معالجة البيانات بنجاح. انقر أدناه لتنزيل التقرير.")
    st.download_button(
        label="\ud83d\udcbe تنزيل التقرير",
        data=processed_data,
        file_name="session_requests_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
