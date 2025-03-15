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

# Upload the Excel file
uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)

    # Load data from Excel sheets
    physical_sessions = pd.read_excel(xls, sheet_name='Physical Sessions')
    connect_sessions_l1 = pd.read_excel(xls, sheet_name='Connect Sessions L1')
    connect_sessions_l2 = pd.read_excel(xls, sheet_name='Connect Sessions L2')
    groups = pd.read_excel(xls, sheet_name='Groups')
    session_requests_l1 = pd.read_excel(xls, sheet_name='Session Requests L1')
    session_requests_l2 = pd.read_excel(xls, sheet_name='Session Requests L2')

    # Clean column names
    groups.columns = groups.columns.str.strip()

    # Convert Event Start Date to datetime format
    physical_sessions["Event Start Date"] = pd.to_datetime(physical_sessions["Event Start Date"])
    connect_sessions_l1["Event Start Date"] = pd.to_datetime(connect_sessions_l1["Event Start Date"])
    connect_sessions_l2["Event Start Date"] = pd.to_datetime(connect_sessions_l2["Event Start Date"])

    # Extract actual weekday from Event Start Date
    connect_sessions_l1["Actual Weekday"] = connect_sessions_l1["Event Start Date"].dt.day_name()
    connect_sessions_l2["Actual Weekday"] = connect_sessions_l2["Event Start Date"].dt.day_name()
    physical_sessions["Actual Weekday"] = physical_sessions["Event Start Date"].dt.day_name()

    # Extract Level, Language, and Grade
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

    # Apply session info extraction to connect sessions
    for df in [connect_sessions_l1, connect_sessions_l2]:
        df[["Level", "Language", "Grade"]] = df.apply(
            lambda row: pd.Series(extract_session_info(row["Session Code"], row["Username"], groups)), axis=1
        )

    # Store results
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
                actual_weekday = student_row["Actual Weekday"]  # Extract actual weekday

                physical_info = physical_sessions[physical_sessions["Username"] == username]
                physical_group = physical_info["Session Code"].values[0] if not physical_info.empty else None
                physical_group_time = physical_info["Event Start Date"].dt.time.values[0] if not physical_info.empty else None

                # Function to find an alternative group
                def find_alternative_group(day, time):
                    possible_groups = groups[
                        (groups["Level"] == level) &
                        (groups["Language Type"] == language) &
                        (groups["Grade"].str.contains(grade.split()[-1], na=False)) &
                        (groups["Weekday"] == day) &  # Ensure matching actual weekday
                        (groups["Event Start Time"] == time)
                    ]
                    for _, group in possible_groups.iterrows():
                        session_code = group["Session Code"]

                        # Skip the same group as before
                        if session_code == old_group:
                            continue  

                        # Ensure no conflict with physical session (min 2.5 hours gap)
                        if physical_group_time is not None:
                            try:
                                time_diff = abs(
                                    (pd.to_datetime(f"2024-01-01 {str(group['Event Start Time'])}") -
                                     pd.to_datetime(f"2024-01-01 {str(physical_group_time)}")).total_seconds()
                                ) / 3600  # Convert to hours

                                if time_diff < 2.5:
                                    continue  # Skip conflicting groups
                            except Exception as e:
                                print(f"Error in time comparison: {e}")

                        # Ensure student count in new group is within limits
                        if session_code not in group_counts:
                            group_counts[session_code] = connect_sessions[connect_sessions["Session Code"] == session_code].shape[0]

                        if 15 < group_counts[session_code] < 35:
                            group_counts[session_code] += 1
                            return session_code, group["Event Start Time"], group_counts[session_code]

                    return None, None, None  # No suitable group found

                # Find a suitable alternative group
                new_group, new_group_time, new_group_count = find_alternative_group(actual_weekday, requested_time)
                if new_group is None:
                    new_group, new_group_time, new_group_count = find_alternative_group(actual_weekday, alternative_time1)
                if new_group is None:
                    new_group, new_group_time, new_group_count = find_alternative_group(actual_weekday, alternative_time2)
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

    # Save the results to an Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        session_requests_l1.to_excel(writer, sheet_name="Session Requests L1", index=False)
        session_requests_l2.to_excel(writer, sheet_name="Session Requests L2", index=False)
        writer.close()
        processed_data = output.getvalue()

    st.write("✅ Data has been processed successfully. Click below to download the report.")
    st.download_button(
        label="📥 Download Report",
        data=processed_data,
        file_name="session_requests_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
