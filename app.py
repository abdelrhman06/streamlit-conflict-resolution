import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime

st.title("📊 Finding Another Group for Students")
st.write("""
Enter the day and time the student wants to find a new group that suits them.
This application was developed by **Abdelrahman Salah**.
Dedicated to **the Connect Team**.
Part of **Almentor**.
""")


uploaded_file = st.file_uploader("Upload the Excel file", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)


    physical_sessions = pd.read_excel(xls, sheet_name='Physical Sessions')
    connect_sessions_l1 = pd.read_excel(xls, sheet_name='Connect Sessions L1')
    connect_sessions_l2 = pd.read_excel(xls, sheet_name='Connect Sessions L2')
    groups = pd.read_excel(xls, sheet_name='Groups')
    session_requests_l1 = pd.read_excel(xls, sheet_name='Session Requests L1')
    session_requests_l2 = pd.read_excel(xls, sheet_name='Session Requests L2')

    
    groups.columns = groups.columns.str.strip()

    
    for df in [physical_sessions, connect_sessions_l1, connect_sessions_l2]:
        df["Event Start Date"] = pd.to_datetime(df["Event Start Date"])
        df["Weekday"] = df["Event Start Date"].dt.day_name().astype(str).str.replace(" ", "")
        df["Event Start Time"] = df["Event Start Date"].dt.strftime("%H:%M:%S")
        df["Event Start Time"] = pd.to_datetime(df["Event Start Time"], format="%H:%M:%S", errors="coerce").dt.time

    groups["Event Start Time"] = pd.to_datetime(groups["Event Start Time"], format="%H:%M:%S", errors="coerce").dt.time
    groups["Weekday"] = groups["Weekday"].astype(str).str.replace(" ", "")

    session_requests_l1["Requested Day"] = session_requests_l1["Requested Day"].astype(str).str.replace(" ", "")
    session_requests_l1["Requested Day2"] = session_requests_l1["Requested Day2"].astype(str).str.replace(" ", "")
    session_requests_l2["Requested Day"] = session_requests_l2["Requested Day"].astype(str).str.replace(" ", "")
    session_requests_l2["Requested Day2"] = session_requests_l2["Requested Day2"].astype(str).str.replace(" ", "")

   
    def determine_language(session_code):
        if pd.isna(session_code):
            return None
        return "Arabic" if "A" in session_code else "English"

    connect_sessions_l1["Language"] = connect_sessions_l1["Session Code"].apply(determine_language)
    connect_sessions_l2["Language"] = connect_sessions_l2["Session Code"].apply(determine_language)

    
    def find_alternative_group(day, time, language, physical_time, group_counts, ignore_conflict=False):
        if pd.isna(time):
            return "No Suitable Group", None, None, None, None
        possible_groups = groups[
            (groups["Weekday"] == day) &
            (groups["Event Start Time"] == time) &
            (groups["Session Code"].apply(determine_language) == language)
        ].copy()
        if possible_groups.empty:
            return "No Suitable Group", None, None, None, None
        possible_groups["Current Student Count"] = possible_groups["Session Code"].map(group_counts).fillna(0).astype(int)
        if not pd.isna(physical_time) and not ignore_conflict:
            possible_groups = possible_groups[
                possible_groups["Event Start Time"].apply(
                    lambda t: abs((pd.to_datetime(t.strftime("%H:%M:%S"), format="%H:%M:%S") - pd.to_datetime(physical_time.strftime("%H:%M:%S"), format="%H:%M:%S")).total_seconds()) / 3600 >= 2.5
                )
            ]
        possible_groups = possible_groups[
            (possible_groups["Current Student Count"] >= 15) &
            (possible_groups["Current Student Count"] <= 35)
        ]
        if not possible_groups.empty:
            best_group = possible_groups.sort_values(by="Current Student Count", ascending=True).iloc[0]
            return (
                best_group["Session Code"],
                best_group["Weekday"],
                best_group["Event Start Time"],
                determine_language(best_group["Session Code"]),
                best_group["Current Student Count"]
            )
        return "No Suitable Group", None, None, None, None

 
    def process_requests(session_requests, connect_sessions, physical_sessions):
        results = []
        group_counts = connect_sessions["Session Code"].value_counts().to_dict()
        for _, row in session_requests.iterrows():
            username = row["Username"]
            requested_day = row["Requested Day"]
            requested_day2 = row["Requested Day2"]
            requested_time = row["Requested Time"]
            alternative_time1 = row["Alternative Time 1"]
            alternative_time2 = row["Alternative Time 2"]
            student_info = connect_sessions[connect_sessions["Username"] == username]
            old_group = student_info.iloc[0]["Session Code"] if not student_info.empty else None
            old_group_language = student_info.iloc[0]["Language"] if not student_info.empty else None
            old_group_time = student_info.iloc[0]["Event Start Time"] if not student_info.empty else None
            physical_info = physical_sessions[physical_sessions["Username"] == username]
            physical_group = physical_info["Session Code"].values[0] if not physical_info.empty else None
            physical_group_time = physical_info["Event Start Time"].values[0] if not physical_info.empty else None
            physical_group_day = physical_info["Weekday"].values[0] if not physical_info.empty else None
            new_group, new_group_day, new_group_time, new_group_language, new_group_count = "No Suitable Group", None, None, None, None
            conflict_flag = False

          
            for day in [requested_day, requested_day2]:
                for time in [requested_time, alternative_time1, alternative_time2]:
                    temp_group, temp_day, temp_time, temp_language, temp_count = find_alternative_group(
                        day, time, old_group_language, physical_group_time, group_counts, ignore_conflict=False
                    )
                    if temp_group != "No Suitable Group":
                        new_group, new_group_day, new_group_time, new_group_language = temp_group, temp_day, temp_time, temp_language
                        group_counts[new_group] = group_counts.get(new_group, 0) + 1
                        if old_group and old_group in group_counts:
                            group_counts[old_group] = max(group_counts[old_group] - 1, 0)
                        new_group_count = group_counts[new_group]
                        break
                if new_group != "No Suitable Group":
                    break

       
            if new_group == "No Suitable Group" and pd.isna(physical_group_time):
                for day in [requested_day, requested_day2]:
                    for time in [requested_time, alternative_time1, alternative_time2]:
                        temp_group, temp_day, temp_time, temp_language, temp_count = find_alternative_group(
                            day, time, old_group_language, physical_group_time, group_counts, ignore_conflict=True
                        )
                        if temp_group != "No Suitable Group":
                            new_group, new_group_day, new_group_time, new_group_language = temp_group, temp_day, temp_time, temp_language
                            group_counts[new_group] = group_counts.get(new_group, 0) + 1
                            if old_group and old_group in group_counts:
                                group_counts[old_group] = max(group_counts[old_group] - 1, 0)
                            new_group_count = group_counts[new_group]
                            conflict_flag = True
                            break
                    if new_group != "No Suitable Group":
                        break

            results.append({
                "Username": username,
                "Requested Day": requested_day,
                "Requested Day2": requested_day2,
                "Requested Time": requested_time,
                "Alternative Time 1": alternative_time1,
                "Alternative Time 2": alternative_time2,
                "Physical Group": physical_group,
                "Physical Group Weekday": physical_group_day,
                "Physical Group Time": physical_group_time,
                "New Group": new_group,
                "New Group Day": new_group_day,
                "New Group Time": new_group_time,
                "New Group Language": new_group_language,
                "New Group Student Count": new_group_count,
                "Conflict": conflict_flag
            })

        return pd.DataFrame(results)

    processed_l1 = process_requests(session_requests_l1, connect_sessions_l1, physical_sessions)
    processed_l2 = process_requests(session_requests_l2, connect_sessions_l2, physical_sessions)

    st.dataframe(processed_l1)
    st.dataframe(processed_l2)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        processed_l1.to_excel(writer, sheet_name="Processed L1", index=False)
        processed_l2.to_excel(writer, sheet_name="Processed L2", index=False)
    output.seek(0)
    st.download_button(
        label="📂 Download Results as Excel",
        data=output,
        file_name="group_reassignment_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )