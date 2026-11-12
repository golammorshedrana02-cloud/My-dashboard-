# EduNexus 2.0

Premium Streamlit + SQLite result dashboard, designed as a V1-compatible upgrade.

## Features
- Admin, Teacher and Student role-based views
- Existing V1 SQLite schema compatibility
- Student directory and quick filtering
- Enter/update subject marks
- Subject-wise grade and grade-point calculation
- GPA summary (average subject grade points; any failed subject marks overall result as Fail)
- Advanced result search
- Merit list and ranking
- PDF marksheet download
- CSV export
- Light/Dark appearance toggle

## Android-friendly workflow
1. Extract this ZIP.
2. Upload `app.py` and `requirements.txt` to a GitHub repository.
3. In Streamlit Community Cloud, create an app from that repository and select `app.py`.
4. Install requirements during deployment automatically.
5. Keep the V1 `edunexus.db` file backed up. For a persistent live deployment, migrate to a hosted database; do not rely on ephemeral local storage.

## Run in a Python environment
```bash
pip install -r requirements.txt
streamlit run app.py
```

## V1 database compatibility
The app uses the same `users`, `students`, and `results` tables as the supplied V1 starter. Keep a backup of the existing `edunexus.db` before upgrading. If deploying to a new host, the database file must be migrated securely.

## Important
This is a prototype, not production-ready institutional software. The grading scale is a generic default and may not match every school, college, university, board, department or course. Configure official grading and credit-weighted GPA rules before use. Add HTTPS, persistent database hosting, audit logs, backups, access reviews, password reset and privacy controls before handling real student records.
