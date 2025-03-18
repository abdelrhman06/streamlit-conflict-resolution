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
   # ✅ **استخراج اللغة من Session Code**
   def determine_language(session_code):
       if pd.isna(session_code):
           return None
       return "Arabic" if "A" in session_code else "English"
   connect_sessions_l1["Language"] = connect_sessions_l1["Session Code"].apply(determine_language)
   connect_sessions_l2["Language"] = connect_sessions_l2["Session Code"].apply(determine_language)
   # ✅ **البحث عن جروب بديل مع التأكد من عدم التعارض**
   def find_alternative_group_with_conflict_fixed(day, time, language, physical_time, group_counts):
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
       if not pd.isna(physical_time):
           possible_groups = possible_groups[
               possible_groups["Event Start Time"].apply(
                   lambda t: abs((pd.to_datetime(t, format="%H:%M:%S") - pd.to_datetime(physical_time, format="%H:%M:%S")).total_seconds()) / 3600 >= 2.5
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
   # ✅ **معالجة الطلبات مع إضافة الأعمدة الجديدة**
   def process_requests_with_full_columns_fixed(session_requests, connect_sessions, physical_sessions):
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
                   temp_group, temp_day, temp_time, temp_language, temp_count = find_alternative_group_with_conflict_fixed(
                       day, time, old_group_language, physical_group_time, group_counts
                   )
                   if temp_group != "No Suitable Group":
                       new_group, new_group_day, new_group_time, new_group_language = temp_group, temp_day, temp_time, temp_language
                       if not pd.isna(physical_group_time) and not pd.isna(temp_time):
                           time_diff = abs((pd.to_datetime(temp_time, format="%H:%M:%S") - pd.to_datetime(physical_group_time, format="%H:%M:%S")).total_seconds()) / 3600
                           if time_diff < 2.5:
                               conflict_flag = True  
                       group_counts[new_group] = group_counts.get(new_group, 0) + 1
                       if old_group and old_group in group_counts:
                           group_counts[old_group] = max(group_counts[old_group] - 1, 0)
                       new_group_count = group_counts[new_group]  
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
   processed_l1 = process_requests_with_full_columns_fixed(session_requests_l1, connect_sessions_l1, physical_sessions)
   processed_l2 = process_requests_with_full_columns_fixed(session_requests_l2, connect_sessions_l2, physical_sessions)
   st.dataframe(processed_l1)
   st.dataframe(processed_l2)