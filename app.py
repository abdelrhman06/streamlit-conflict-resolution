import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta

st.title("📊 Finding Another Group for Students")
st.write("""
Enter the day and time the student wants to find a new group that suits them.  

This application was developed by **Abdelrahman Salah**.  
Dedicated to **the Connect Team**.  

Part of **Almentor**.
""")

uploaded_file = st.file_uploader("📂 Upload an Excel file", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)

    physical_sessions = pd.read_excel(xls, sheet_name='Physical Sessions')
    connect_sessions_l1 = pd.read_excel(xls, sheet_name='Connect Sessions L1')
    connect_sessions_l2 = pd.read_excel(xls, sheet_name='Connect Sessions L2')
    groups = pd.read_excel(xls, sheet_name='Groups')
    session_requests_l1 = pd.read_excel(xls, sheet_name='Session Requests L1')
    session_requests_l2 = pd.read_excel(xls, sheet_name='Session Requests L2')

    groups.columns = groups.columns.str.strip()
    physical_sessions["Event Start Date"] = pd.to_datetime(physical_sessions["Event Start Date"])
    connect_sessions_l1["Event Start Date"] = pd.to_datetime(connect_sessions_l1["Event Start Date"])
    connect_sessions_l2["Event Start Date"] = pd.to_datetime(connect_sessions_l2["Event Start Date"])

    def get_day_from_session_code(session_code):
        day_map = {
            "F": "Friday", "S": "Saturday", "M": "Monday",
            "T": "Tuesday", "W": "Wednesday", "Th": "Thursday", "Su": "Sunday"
        }
        for key, value in day_map.items():
            if key in session_code:
                return value
        return "Unknown"

    def extract_session_info(session_code, username, df_groups):
        if isinstance(session_code, str):
            group_info = df_groups[df_groups["Session Code"] == session_code]
            if not group_info.empty:
                level = group_info.iloc[0]["Level"]
                language = group_info.iloc[0].get("Language Type", group_info.iloc[0].get("Language", "Unknown"))
                grade = group_info.iloc[0].get("Grade", "Unknown")
            else:
                level = "Level 2" if session_code[1].isdigit() else "Level 1"
                language = "Arabic" if "A" in session_code else "English"
                grade = "Unknown"

            if grade == "Unknown":
                grade_match = re.search(r"G(\d+)", username)
                grade = f"Grade {grade_match.group(1)}" if grade_match else "Unknown"

            return level, language, grade, get_day_from_session_code(session_code)
        return None, None, None, "Unknown"

    for df in [connect_sessions_l1, connect_sessions_l2]:
        df[["Level", "Language", "Grade", "Weekday"]] = df.apply(lambda row: pd.Series(extract_session_info(row["Session Code"], row["Username"], groups)), axis=1)

    physical_sessions["Weekday"] = physical_sessions["Event Start Date"].dt.day_name()

    def is_conflict(new_day, new_time, physical_day, physical_time):
        if new_day == physical_day:
            time_diff = abs((datetime.combine(datetime.today(), new_time) - datetime.combine(datetime.today(), physical_time)).total_seconds()) / 3600
            return time_diff < 2.5
        return False

    st.success("✅ Data processed successfully!")