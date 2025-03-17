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
        df["Event Start Date"] = pd.to_datetime(df["Event Start Date"], errors='coerce')
        df["Weekday"] = df["Event Start Date"].dt.day_name()
        df["Event Start Time"] = pd.to_datetime(df["Event Start Date"].dt.strftime("%H:%M:%S"), format="%H:%M:%S", errors="coerce").dt.time
    
    groups["Event Start Time"] = pd.to_datetime(groups["Event Start Time"], format="%H:%M:%S", errors="coerce").dt.time
    
    # Optimized processing function
    def find_alternative_group(row, groups, current_sessions):
        """Find an alternative group for a student based on requested time and availability."""
        requested_times = [row["Requested Time"], row["Alternative Time 1"], row.get("Alternative Time 2", None)]
        possible_groups = groups[groups["Weekday"].isin([row["Requested Day"], row["Requested Day2"]])]
        
        for time in requested_times:
            if pd.isna(time):
                continue
            
            available_groups = possible_groups[possible_groups["Event Start Time"] == time]
            for _, group in available_groups.iterrows():
                session_code = group["Session Code"]
                if session_code in current_sessions:
                    continue
                
                return session_code, group["Event Start Time"]
        
        return "No Suitable Group", None
    
    def process_requests(session_requests, connect_sessions):
        """Process all session requests and assign new groups where possible."""
        current_sessions = set(connect_sessions["Session Code"])
        results = []
        
        for _, row in session_requests.iterrows():
            new_group, new_time = find_alternative_group(row, groups, current_sessions)
            results.append({
                "Username": row["Username"],
                "Old Group": connect_sessions.loc[connect_sessions["Username"] == row["Username"], "Session Code"].values[0] if row["Username"] in connect_sessions["Username"].values else None,
                "Requested Day": row["Requested Day"],
                "New Group": new_group,
                "New Group Time": new_time
            })
        
        return pd.DataFrame(results)
    
    processed_l1 = process_requests(session_requests_l1, connect_sessions_l1)
    processed_l2 = process_requests(session_requests_l2, connect_sessions_l2)
    
    output_buffer = io.BytesIO()
    with pd.ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
        processed_l1.to_excel(writer, sheet_name="Session Requests L1", index=False)
        processed_l2.to_excel(writer, sheet_name="Session Requests L2", index=False)
    output_buffer.seek(0)
    
    st.download_button(
        label="💾 Download Processed Data",
        data=output_buffer,
        file_name="session_requests_fixed.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
