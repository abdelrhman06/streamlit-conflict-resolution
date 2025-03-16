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

# Upload file
uploaded_file = st.file_uploader("Upload the Excel file", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    
    # Load data
    physical_sessions = pd.read_excel(xls, sheet_name='Physical Sessions')
    connect_sessions_l1 = pd.read_excel(xls, sheet_name='Connect Sessions L1')
    connect_sessions_l2 = pd.read_excel(xls, sheet_name='Connect Sessions L2')
    groups = pd.read_excel(xls, sheet_name='Groups')
    session_requests_l1 = pd.read_excel(xls, sheet_name='Session Requests L1')
    session_requests_l2 = pd.read_excel(xls, sheet_name='Session Requests L2')
    
    # Clean column names
    groups.columns = groups.columns.str.strip()
    
    # Convert date and time columns
    for df in [physical_sessions, connect_sessions_l1, connect_sessions_l2]:
        df["Event Start Date"] = pd.to_datetime(df["Event Start Date"])
        df["Weekday"] = df["Event Start Date"].dt.day_name()
        df["Event Start Time"] = df["Event Start Date"].dt.strftime("%H:%M:%S")
        df["Event Start Time"] = pd.to_datetime(df["Event Start Time"], format="%H:%M:%S", errors="coerce").dt.time
    
    groups["Event Start Time"] = pd.to_datetime(groups["Event Start Time"], format="%H:%M:%S", errors="coerce").dt.time
    
    # Processing function
    def process_requests(session_requests, connect_sessions):
        results = []
        group_counts = {}
        group_details = []
        
        for _, row in session_requests.iterrows():
            username = row["Username"]
            requested_day = row["Requested Day"]
            requested_day2 = row["Requested Day2"]
            requested_time = row["Requested Time"]
            alternative_time1 = row["Alternative Time 1"]
            alternative_time2 = row.get("Alternative Time 2", None)
            
            student_info = connect_sessions[connect_sessions["Username"] == username]
            old_group = student_info.iloc[0]["Session Code"] if not student_info.empty else None
            old_group_time = student_info.iloc[0]["Event Start Time"] if not student_info.empty else None
            
            physical_info = physical_sessions[physical_sessions["Username"] == username]
            physical_group = physical_info["Session Code"].values[0] if not physical_info.empty else None
            physical_group_time = physical_info["Event Start Time"].values[0] if not physical_info.empty else None
            
            def find_alternative_group(day, time):
                if pd.isna(time):
                    return None, None, None
                possible_groups = groups[(groups["Weekday"] == day) & (groups["Event Start Time"] == time)]
                for _, group in possible_groups.iterrows():
                    session_code = group["Session Code"]
                    if session_code == old_group:
                        continue
                    if session_code not in group_counts:
                        group_counts[session_code] = connect_sessions[connect_sessions["Session Code"] == session_code].shape[0]
                    if 15 < group_counts[session_code] < 35:
                        if physical_group_time is None or abs((pd.to_datetime(f"2024-01-01 {str(group['Event Start Time'])}") - pd.to_datetime(f"2024-01-01 {str(physical_group_time)}")).total_seconds()) / 3600 >= 2.5:
                            group_counts[session_code] += 1
                            return session_code, group["Event Start Time"], group_counts[session_code]
                return None, None, None
            
            new_group, new_group_time, new_group_count = find_alternative_group(requested_day, requested_time) or (None, None, None)
            if new_group is None:
                new_group, new_group_time, new_group_count = find_alternative_group(requested_day, alternative_time1) or (None, None, None)
            if new_group is None:
                new_group, new_group_time, new_group_count = find_alternative_group(requested_day, alternative_time2) or (None, None, None)
            
            if new_group is None:
                new_group, new_group_time, new_group_count = find_alternative_group(requested_day2, requested_time) or (None, None, None)
            if new_group is None:
                new_group, new_group_time, new_group_count = find_alternative_group(requested_day2, alternative_time1) or (None, None, None)
            if new_group is None:
                new_group, new_group_time, new_group_count = find_alternative_group(requested_day2, alternative_time2) or ("No Suitable Group", None, None)
            
            results.append({
                "Username": username,
                "Old Group": old_group,
                "Old Group Time": old_group_time,
                "Physical Group": physical_group,
                "Physical Group Time": physical_group_time,
                "Requested Day": requested_day,
                "Requested Day2": requested_day2,
                "Requested Time": requested_time,
                "New Group": new_group,
                "New Group Time": new_group_time,
                "New Group Student Count": new_group_count
            })
        
        return pd.DataFrame(results)
    
    # Process requests
    processed_l1 = process_requests(session_requests_l1, connect_sessions_l1)
    processed_l2 = process_requests(session_requests_l2, connect_sessions_l2)
    
    # Save results to Excel
    output_buffer = io.BytesIO()
    with pd.ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
        processed_l1.to_excel(writer, sheet_name="Session Requests L1", index=False)
        processed_l2.to_excel(writer, sheet_name="Session Requests L2", index=False)
    output_buffer.seek(0)
    
  # Download button
    st.download_button(
        label="📥 Download Processed Data",
        data=output_buffer,
        file_name="session_requests_final_updated.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
