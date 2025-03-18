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
       df["Weekday"] = df["Event Start Date"].dt.day_name()  # استخراج اليوم
       df["Event Start Time"] = df["Event Start Date"].dt.strftime("%H:%M:%S")
       df["Event Start Time"] = pd.to_datetime(df["Event Start Time"], format="%H:%M:%S", errors="coerce").dt.time
   groups["Event Start Time"] = pd.to_datetime(groups["Event Start Time"], format="%H:%M:%S", errors="coerce").dt.time
   # ✅ **استخراج اللغة من Session Code**
   def determine_language(session_code):
       if pd.isna(session_code):
           return None
       return "Arabic" if "A" in session_code else "English"
   connect_sessions_l1["Language"] = connect_sessions_l1["Session Code"].apply(determine_language)
   connect_sessions_l2["Language"] = connect_sessions_l2["Session Code"].apply(determine_language)
   # ✅ **معالجة الطلبات**
   def process_requests(session_requests, connect_sessions):
       results = []
       group_counts = {session_code: connect_sessions[connect_sessions["Session Code"] == session_code].shape[0]
                       for session_code in groups["Session Code"].unique()}
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
           old_group_language = student_info.iloc[0]["Language"] if not student_info.empty else None
           # ✅ **البحث عن جروب بديل**
           def find_alternative_group(day, time, language):
               if pd.isna(time):
                   return None, None, None, None
               possible_groups = groups[
                   (groups["Weekday"] == day) &
                   (groups["Event Start Time"] == time) &
                   (groups["Session Code"].apply(determine_language) == language)
               ]
               for _, group in possible_groups.iterrows():
                   session_code = group["Session Code"]
                   if session_code == old_group:
                       continue
                   if 15 < group_counts.get(session_code, 0) < 35:
                       group_counts[session_code] += 1
                       return session_code, group["Event Start Time"], group_counts[session_code], determine_language(session_code)
               return None, None, None, None
           new_group, new_group_time, new_group_count, new_group_language = find_alternative_group(requested_day, requested_time, old_group_language) or (None, None, None, None)
           if new_group is None:
               new_group, new_group_time, new_group_count, new_group_language = find_alternative_group(requested_day, alternative_time1, old_group_language) or (None, None, None, None)
           if new_group is None:
               new_group, new_group_time, new_group_count, new_group_language = find_alternative_group(requested_day, alternative_time2, old_group_language) or (None, None, None, None)
           if new_group is None:
               new_group, new_group_time, new_group_count, new_group_language = find_alternative_group(requested_day2, requested_time, old_group_language) or (None, None, None, None)
           if new_group is None:
               new_group, new_group_time, new_group_count, new_group_language = find_alternative_group(requested_day2, alternative_time1, old_group_language) or (None, None, None, None)
           if new_group is None:
               new_group, new_group_time, new_group_count, new_group_language = find_alternative_group(requested_day2, alternative_time2, old_group_language) or ("No Suitable Group", None, None, None)
           results.append({
               "Username": username,
               "Old Group": old_group,
               "Old Group Language": old_group_language,
               "Requested Day": requested_day,
               "Requested Day2": requested_day2,
               "Requested Time": requested_time,
               "Alternative Time 1": alternative_time1,
               "Alternative Time 2": alternative_time2,
               "New Group": new_group,
               "New Group Time": new_group_time,
               "New Group Language": new_group_language,
               "New Group Student Count": new_group_count
           })
       return pd.DataFrame(results)
   # ✅ **إنشاء بيانات الجروبات قبل وبعد التوزيع**
   def generate_group_details():
       all_sessions = pd.concat([connect_sessions_l1, connect_sessions_l2])
       initial_counts = all_sessions["Session Code"].value_counts().reset_index()
       initial_counts.columns = ["Session Code", "Initial Student Count"]
       final_counts = processed_l1["New Group"].value_counts().add(
           processed_l2["New Group"].value_counts(), fill_value=0
       ).reset_index()
       final_counts.columns = ["Session Code", "Final Student Count"]
       group_details = groups.merge(initial_counts, on="Session Code", how="left").merge(final_counts, on="Session Code", how="left")
       group_details["Initial Student Count"] = group_details["Initial Student Count"].fillna(0).astype(int)
       group_details["Final Student Count"] = group_details["Final Student Count"].fillna(0).astype(int)
       group_details["Change"] = group_details["Final Student Count"] - group_details["Initial Student Count"]
       group_details["Action"] = group_details["Change"].apply(lambda x: "Increased" if x > 0 else "Decreased" if x < 0 else "No Change")
       return group_details
   processed_l1 = process_requests(session_requests_l1, connect_sessions_l1)
   processed_l2 = process_requests(session_requests_l2, connect_sessions_l2)
   group_details_final = generate_group_details()
   st.dataframe(group_details_final)