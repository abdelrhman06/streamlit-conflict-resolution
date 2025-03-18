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
# 📌 **تحميل الملف**
uploaded_file = st.file_uploader("Upload the Excel file", type=["xlsx"])
if uploaded_file:
   xls = pd.ExcelFile(uploaded_file)
   # ✅ **تحميل البيانات**
   physical_sessions = pd.read_excel(xls, sheet_name='Physical Sessions')
   connect_sessions_l1 = pd.read_excel(xls, sheet_name='Connect Sessions L1')
   connect_sessions_l2 = pd.read_excel(xls, sheet_name='Connect Sessions L2')
   groups = pd.read_excel(xls, sheet_name='Groups')
   session_requests_l1 = pd.read_excel(xls, sheet_name='Session Requests L1')
   session_requests_l2 = pd.read_excel(xls, sheet_name='Session Requests L2')
   # ✅ **تنظيف أسماء الأعمدة**
   groups.columns = groups.columns.str.strip()
   # ✅ **تحويل التواريخ والأوقات**
   for df in [physical_sessions, connect_sessions_l1, connect_sessions_l2]:
       df["Event Start Date"] = pd.to_datetime(df["Event Start Date"])
       df["Weekday"] = df["Event Start Date"].dt.day_name()
       df["Event Start Time"] = df["Event Start Date"].dt.strftime("%H:%M:%S")
       df["Event Start Time"] = pd.to_datetime(df["Event Start Time"], format="%H:%M:%S", errors="coerce").dt.time
   groups["Event Start Time"] = pd.to_datetime(groups["Event Start Time"], format="%H:%M:%S", errors="coerce").dt.time
   # ✅ **تحديد اللغة في Connect Sessions**
   def determine_language(session_code, level):
       if pd.isna(session_code):
           return None
       if level == "L1":
           return "Arabic" if session_code[1] == "A" else "English"
       elif level == "L2":
           return "Arabic" if session_code[2] == "A" else "English"
       return None
   connect_sessions_l1["Language"] = connect_sessions_l1["Session Code"].apply(lambda x: determine_language(x, "L1"))
   connect_sessions_l2["Language"] = connect_sessions_l2["Session Code"].apply(lambda x: determine_language(x, "L2"))
   # ✅ **معالجة الطلبات**
   def process_requests(session_requests, connect_sessions):
       results = []
       group_counts = {session_code: connect_sessions[connect_sessions["Session Code"] == session_code].shape[0] for session_code in groups["Session Code"].unique()}
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
           old_group_language = student_info.iloc[0]["Language"] if not student_info.empty else None
           physical_info = physical_sessions[physical_sessions["Username"] == username]
           physical_group = physical_info["Session Code"].values[0] if not physical_info.empty else None
           physical_group_time = physical_info["Event Start Time"].values[0] if not physical_info.empty else None
           # ✅ **البحث عن جروب بديل بنفس اللغة**
           def find_alternative_group(day, time, language):
               if pd.isna(time):
                   return None, None, None, None
               possible_groups = groups[(groups["Weekday"] == day) & (groups["Event Start Time"] == time)]
               possible_groups = possible_groups[possible_groups["Session Code"].apply(lambda x: determine_language(x, "L1") if "L1" in x else determine_language(x, "L2")) == language]
               for _, group in possible_groups.iterrows():
                   session_code = group["Session Code"]
                   if session_code == old_group:
                       continue
                   if 15 < group_counts.get(session_code, 0) < 35:
                       if physical_group_time is None or abs((datetime.combine(datetime.today(), group["Event Start Time"]) - datetime.combine(datetime.today(), physical_group_time)).total_seconds()) / 3600 >= 2.5:
                           group_counts[session_code] += 1
                           new_language = determine_language(session_code, "L1") if "L1" in session_code else determine_language(session_code, "L2")
                           return session_code, group["Event Start Time"], group_counts[session_code], new_language
               return None, None, None, None
           new_group, new_group_time, new_group_count, new_group_language = find_alternative_group(requested_day, requested_time, old_group_language) or (None, None, None, None)
           if new_group != "No Suitable Group" and old_group in group_counts:
               group_counts[old_group] -= 1
           results.append({
               "Username": username,
               "Old Group": old_group,
               "Old Group Time": old_group_time,
               "Old Group Language": old_group_language,
               "Physical Group": physical_group,
               "Physical Group Time": physical_group_time,
               "Requested Day": requested_day,
               "Requested Day2": requested_day2,
               "Requested Time": requested_time,
               "New Group": new_group,
               "New Group Time": new_group_time,
               "New Group Language": new_group_language,
               "New Group Student Count": new_group_count
           })
       return pd.DataFrame(results)
   processed_l1 = process_requests(session_requests_l1, connect_sessions_l1)
   processed_l2 = process_requests(session_requests_l2, connect_sessions_l2)
   # ✅ **حساب Final Student Count بعد التعديلات**
   all_connect_sessions = pd.concat([connect_sessions_l1, connect_sessions_l2])
   group_details = all_connect_sessions.groupby("Session Code").size().reset_index(name="Initial Student Count")
   group_details["Final Student Count"] = group_details["Session Code"].apply(lambda x: (processed_l1["New Group"].tolist() + processed_l2["New Group"].tolist()).count(x))
   group_details["Change"] = group_details["Final Student Count"] - group_details["Initial Student Count"]
   # ✅ **تحميل الملف النهائي**
   output_buffer = io.BytesIO()
   with pd.ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
       processed_l1.to_excel(writer, sheet_name="Session Requests L1", index=False)
       processed_l2.to_excel(writer, sheet_name="Session Requests L2", index=False)
       group_details.to_excel(writer, sheet_name="Group Details", index=False)
   output_buffer.seek(0)
   st.download_button(
       label="💾 Download Processed Data",
       data=output_buffer,
       file_name="session_requests_fixed.xlsx",
       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
   )