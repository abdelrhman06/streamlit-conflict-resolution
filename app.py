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

# 📂 **رفع ملف الإكسل**
uploaded_file = st.file_uploader("Upload the Excel file", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)

    # 🟢 **تحميل البيانات**
    physical_sessions = pd.read_excel(xls, sheet_name='Physical Sessions')
    connect_sessions_l1 = pd.read_excel(xls, sheet_name='Connect Sessions L1')
    connect_sessions_l2 = pd.read_excel(xls, sheet_name='Connect Sessions L2')
    session_requests_l1 = pd.read_excel(xls, sheet_name='Session Requests L1')
    session_requests_l2 = pd.read_excel(xls, sheet_name='Session Requests L2')

    # 🟢 **استخراج بيانات الجروبات من Connect Sessions**
    connect_sessions = pd.concat([connect_sessions_l1, connect_sessions_l2])
    groups = connect_sessions[['Session Code', 'Event Start Date']].drop_duplicates()
    groups['Event Start Date'] = pd.to_datetime(groups['Event Start Date'])
    groups['Weekday'] = groups['Event Start Date'].dt.day_name()
    groups['Event Start Time'] = groups['Event Start Date'].dt.time

    # 🟢 **تحويل التوقيتات إلى Time فقط**
    def convert_to_time(df, column):
        df[column] = pd.to_datetime(df[column], errors='coerce').dt.time
        return df

    for df in [physical_sessions, session_requests_l1, session_requests_l2]:
        df = convert_to_time(df, 'Requested Time')
        df = convert_to_time(df, 'Alternative Time 1')
        df = convert_to_time(df, 'Alternative Time 2')

    # 🟢 **دالة البحث عن الجروب الجديد**
    def process_requests(session_requests, connect_sessions):
        results = []
        group_counts = connect_sessions['Session Code'].value_counts().to_dict()
        group_details = []

        for _, row in session_requests.iterrows():
            username = row["Username"]
            requested_day = row["Requested Day"]
            requested_day2 = row["Requested Day2"]
            requested_times = [row["Requested Time"], row["Alternative Time 1"], row["Alternative Time 2"]]

            student_info = connect_sessions[connect_sessions["Username"] == username]
            old_group = student_info.iloc[0]["Session Code"] if not student_info.empty else None
            old_group_time = student_info.iloc[0]["Event Start Time"] if not student_info.empty else None

            physical_info = physical_sessions[physical_sessions["Username"] == username]
            physical_group = physical_info["Session Code"].values[0] if not physical_info.empty else None
            physical_group_time = physical_info["Event Start Time"].values[0] if not physical_info.empty else None

            new_group, new_group_time, new_group_count = None, None, None

            # 🟢 **البحث عن الجروب الجديد بطريقة منظمة**
            for day in [requested_day, requested_day2]:
                for time_option in requested_times:
                    if pd.isna(time_option):
                        continue
                    possible_groups = groups[(groups["Weekday"] == day) & (groups["Event Start Time"] == time_option)]
                    for _, group in possible_groups.iterrows():
                        session_code = group["Session Code"]
                        if session_code == old_group:
                            continue
                        if group_counts.get(session_code, 0) < 35:
                            if physical_group_time is None or abs(
                                    (datetime.combine(datetime.today(), group["Event Start Time"]) - datetime.combine(datetime.today(), physical_group_time)).total_seconds()) / 3600 >= 2.5:
                                group_counts[session_code] = group_counts.get(session_code, 0) + 1
                                new_group, new_group_time, new_group_count = session_code, group["Event Start Time"], group_counts[session_code]
                                break
                    if new_group:
                        break
                if new_group:
                    break

            if new_group is None:
                new_group, new_group_time, new_group_count = "No Suitable Group", None, None

            results.append({
                "Username": username,
                "Old Group": old_group,
                "Old Group Time": old_group_time,
                "Physical Group": physical_group,
                "Physical Group Time": physical_group_time,
                "Requested Day": requested_day,
                "Requested Day2": requested_day2,
                "Requested Time": row["Requested Time"],
                "Alternative Time 1": row["Alternative Time 1"],
                "Alternative Time 2": row["Alternative Time 2"],
                "New Group": new_group,
                "New Group Time": new_group_time,
                "New Group Student Count": new_group_count
            })

        # 🟢 **إعداد بيانات Group Details**
        for session_code, count in group_counts.items():
            initial_count = connect_sessions[connect_sessions["Session Code"] == session_code].shape[0]
            group_time = groups.loc[groups["Session Code"] == session_code, "Event Start Time"].values[0]
            group_details.append({
                "Session Code": session_code,
                "Event Start Time": group_time,
                "Initial Student Count": initial_count,
                "Final Student Count": count,
                "Change": count - initial_count
            })

        return pd.DataFrame(results), pd.DataFrame(group_details)

    # 🟢 **تنفيذ عملية البحث عن الجروبات الجديدة**
    processed_l1, group_details_l1 = process_requests(session_requests_l1, connect_sessions_l1)
    processed_l2, group_details_l2 = process_requests(session_requests_l2, connect_sessions_l2)

    # 🟢 **حفظ النتائج إلى ملف Excel**
    output_buffer = io.BytesIO()
    with pd.ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
        processed_l1.to_excel(writer, sheet_name="Session Requests L1", index=False)
        processed_l2.to_excel(writer, sheet_name="Session Requests L2", index=False)
        pd.concat([group_details_l1, group_details_l2]).to_excel(writer, sheet_name="Group Details", index=False)
    output_buffer.seek(0)

    # 🟢 **عرض النتائج في Streamlit**
    st.write("### Group Details")
    st.dataframe(pd.concat([group_details_l1, group_details_l2]))

    st.download_button(
        label="💾 Download Processed Data",
        data=output_buffer,
        file_name="session_requests_fixed.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
