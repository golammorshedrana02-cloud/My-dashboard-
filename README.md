# EduNexus V3.0 — Fresh Build

## Included
- Fresh SQLite database
- Admin, Teacher, Student login roles
- Student account creation
- Marks entry/update
- Student result view
- Subject performance chart
- Rule-based explainable insights (not ML prediction)
- CSV export and dark mode

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy
Upload files to GitHub, then create a Streamlit Community Cloud app using `app.py`.

## Safety and limitations
This is a learning prototype, not production-ready. The default grade scale is illustrative, not an official Bangladesh board/university policy. SQLite on free hosting may not persist reliably. Do not use real student records until authorized access, persistent database hosting, HTTPS, backups, audit logs and privacy controls are implemented.
