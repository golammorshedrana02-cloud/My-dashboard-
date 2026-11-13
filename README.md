# EduNexus V4.0 — Fresh Academic Management Prototype

## Features
- Admin / Teacher / Student roles
- First-run Admin setup and PBKDF2 password hashing
- Student directory and CSV bulk import
- Class-wise subject setup and exam sessions
- Marks entry and update
- Student result view
- Announcements
- Academic overview, CSV export and activity log
- Rule-based grade labels (generic demo scale)

## Run on Android
1. Install/open a browser and visit https://github.com
2. Create a repository named `edunexus-v4`.
3. Upload `app.py` and `requirements.txt`.
4. Visit https://share.streamlit.io and sign in with GitHub.
5. Choose the repository, branch `main`, and main file `app.py`.
6. Deploy. On first launch, create the Admin account.

For local Android experimentation, a Python environment such as Pydroid may work, but Streamlit deployment through GitHub + Streamlit Community Cloud is the simplest beginner route.

## Requirements
- Python 3.10+
- streamlit
- pandas

## Important limitations
This is a learning/prototype build, not a production student information system.
- The demo grading scale is not an official Bangladesh board or university scale.
- SQLite file persistence on free hosting may not be guaranteed across rebuilds/restarts.
- The starter has role-based navigation, but it is not a complete enterprise authorization/security system.
- No ML prediction is claimed. Charts and reports are descriptive; grades are rule-based.
- Before real student records: use persistent managed database storage, HTTPS, strong account lifecycle controls, institution isolation, least-privilege permissions, backups, audit review, privacy/legal review, and security testing.
- Use fictional data while testing. Never commit the database or real student data to a public GitHub repository.
