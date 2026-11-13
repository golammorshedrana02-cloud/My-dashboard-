# EduNexus V6.0

## V6 additions
- Admin-controlled result publishing: exams start as Draft.
- Admin reviews entered marks and explicitly publishes results.
- Student accounts see only published exam results.
- Admin can unpublish results if a correction is needed.
- Exam-wise merit list with rank, obtained marks, total marks and percentage.
- V5 premium light theme and mobile-responsive CSS retained.
- V5 database filename/schema retained; startup adds `is_published` column when missing.

## Update from V5 using Android
1. Back up your existing database if you have a local copy. Do not overwrite or delete it.
2. Upload/replace `app.py` and `requirements.txt` in your existing GitHub repository.
3. Keep the `.streamlit/config.toml` file from V5, or replace it with the included one.
4. Commit changes, then reboot the Streamlit app.

## Important migration note
The app keeps the V5 SQLite filename (`edunexus_v4.db`) for local compatibility. On startup, existing exam rows are marked Draft if the publication column is newly added. Admin must review and publish them. Free-hosting SQLite persistence is not guaranteed; verify the database and take backups before updating a live system.

## Limitations
This remains a prototype, not a production student information system. The grade scale is generic/demo only. Merit list percentages are based on the marks currently entered; missing subject marks can affect rankings. Use fictional data during testing. Real student records require persistent managed storage, HTTPS, backups, secure account lifecycle, strict role authorization, institution isolation, privacy review and security testing.
