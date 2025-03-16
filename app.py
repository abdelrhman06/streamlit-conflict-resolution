import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime

st.title("📊 Finding Another Group for Students")
st.write("""
Enter the day and time the student wants to find a new group that suits them.  

This application was developed by **Abdelrahman Salah**.  
Dedicated to **the Connect Team**.  

Part of **Almentor**.
""")

# Upload the Excel file
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)

    # Load data from sheets
    physical_sessions = pd.read_excel(xls, sheet_name='Physical Sessions')
    connect_sessions_l1 = pd.read_excel(xls, sheet_name='Connect Sessions L1')
    connect_sessions_l2 = pd.read_excel(xls, sheet_name='Connect Sessions L2')
    groups = pd.read_excel(xls, sheet_name='Groups')
    session_requests_l1 = pd.read_excel(xls, sheet_name='Session Requests L1')
    session_requests_l2 = pd.read_excel(xls, sheet_name='Session Requests L2')

    # Clean column names in groups table
    groups.columns = groups.columns.str.strip()

    # Convert event start dates to datetime
    for df in [physical_sessions, connect_sessions_l1, connect_sessions_l2]:
        df["Event Start Date"] = pd.to_datetime(df["Event Start Date"])
        df["Weekday"] = df["Event Start Date"].dt.day_name()  # Extract actual weekday

    # Extract level, language, and grade from session code
    def extract_session_info(session_code, username, df_groups):
        if isinstance(session_code, str):
            group_info = df_groups[df_groups["Session Code"] == session_code]
            if not group_info.empty:
                level = group_info.iloc[0]["Level"]
                language = group_info.iloc[0].get("Language Type", group_info.iloc[0].get("Language"))
                grade = group_info.iloc[0].get("Grade")
            else:
                level = "Level 2" if session_code[1].isdigit() else "Level 1"
                language = "Arabic" if "A" in session_code else "English"
                grade = None

            if grade is None:
                grade_match = re.search(r"G(\d+)", username)
                grade = f"Grade {grade_match.group(1)}" if grade_match else "Unknown"

            return level, language, grade
        return None, None, None

    for df in [connect_sessions_l1, connect_sessions_l2]:
        df[["Level", "Language", "Grade"]] = df.apply(
            lambda row: pd.Series(extract_session_info(row["Session Code"], row["Username"], groups)), axis=1
        )

    # Create results dictionary
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
                old_group_day = student_row["Weekday"]
                physical_info = physical_sessions[physical_sessions["Username"] == username]
                physical_group = physical_info["Session Code"].values[0] if not physical_info.empty else None
                physical_group_time = physical_info["Event Start Date"].dt.time.values[0] if not physical_info.empty else None

                def find_alternative_group(day, time):
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
                            continue  # Avoid selecting the same old group
                        if session_code not in group_counts:
                            group_counts[session_code] = connect_sessions[connect_sessions["Session Code"] == session_code].shape[0]
                        if 15 < group_counts[session_code] < 35:
                            if physical_group_time is None or abs(
                                (pd.to_datetime(f"2024-01-01 {group['Event Start Time']}") - pd.to_datetime(f"2024-01-01 {physical_group_time}"))
                                .total_seconds()) / 3600 >= 2.5:
                                group_counts[session_code] += 1
                                return session_code, group["Event Start Time"], group_counts[session_code], False
                    return None, None, None, True

                new_group, new_group_time, new_group_count, conflict = find_alternative_group(requested_day, requested_time)
                if new_group is None:
                    new_group, new_group_time, new_group_count, conflict = find_alternative_group(requested_day, alternative_time1)
                if new_group is None:
                    new_group, new_group_time, new_group_count, conflict = find_alternative_group(requested_day, alternative_time2)
                if new_group is None:
                    new_group, new_group_time, new_group_count, conflict = "No Suitable Group", None, None, False

                session_requests.loc[session_requests["Username"] == username, [
                    "New Group", "New Group Time", "New Group Student Count",
                    "Old Group", "Old Group Time", "Physical Group", "Physical Group Time", "Conflict"
                ]] = [
                    new_group, new_group_time, new_group_count,
                    old_group, old_group_time, physical_group, physical_group_time, conflict
                ]
                sheets[sheet_name] = pd.concat([sheets[sheet_name], session_requests[session_requests["Username"] == username]], ignore_index=True)

    # Save the results
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        writer.close()
        processed_data = output.getvalue()

    st.write("✅ Data has been processed successfully. Click below to download the report.")
    st.download_button(
        label="📥 Download Report",
        data=processed_data,
        file_name="session_requests_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
