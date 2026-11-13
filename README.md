# EduNexus V7.0 — Academic Management + Attendance

## V7.0 additions
- Announcement card contrast fix: dark readable text on white card; explicit empty state.
- Alert contrast fix: dark navy alert background with white readable text.
- Daily Attendance module for Admin and Teacher: class-wise date-based Present / Absent / Late.
- Attendance updates are unique per student per date (re-saving updates the same record).
- Student portal includes My Attendance with attendance rate, present/absent/late counts.
- Attendance CSV export for staff and individual student.
- Dashboard includes today's attendance record count.
- Preserves V6 controlled result publishing, result review/unpublish, exam-wise merit list,
  V5 responsive styling, student/subject/exam management, roles, announcements and audit trail.

## Update from V6 using Android
1. Download and extract this ZIP.
2. In the existing GitHub repository, replace `app.py` and `requirements.txt`.
3. Keep/replace `.streamlit/config.toml` with the included file.
4. Commit the changes and reboot the Streamlit app.
5. Do not delete your existing database. This app retains the V6 database filename and adds
   an attendance table automatically when it starts.

## Testing status
Python syntax compilation passed. This is not a full Streamlit runtime or live-hosting test.

## Important
Prototype only. The grade scale is generic/demo. SQLite persistence on free hosting is not guaranteed.
Back up the database before updating. Do not use real student records until persistent managed
storage, HTTPS, backups, strong account recovery, strict role permissions, institution isolation,
privacy review and security testing are completed. Use fictional data during testing.
