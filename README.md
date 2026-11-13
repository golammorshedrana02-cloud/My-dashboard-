# EduNexus V5.0 — Premium Mobile-Responsive Academic Management

## V5.0 updates
- Fixed light/dark theme contrast by explicitly configuring Streamlit's light theme.
- Reworked dashboard colors for readable dark text on pale backgrounds and white metric cards.
- Added responsive spacing, typography, metric sizing, and full-width mobile buttons.
- Preserves V4 features: Admin/Teacher/Student roles, student directory, CSV bulk import,
  subjects, exams, marks entry, student results, announcements, analytics, CSV export, and audit log.

## Deploy / update using Android
1. Open your existing GitHub repository for EduNexus.
2. Upload/replace `app.py` and `requirements.txt`.
3. Create a folder named `.streamlit` in the repository root.
4. Inside it, add `config.toml` using the file included in this ZIP.
5. Commit the changes.
6. Open Streamlit Community Cloud and reboot/redeploy the app.

If starting fresh, create a repository, upload all files including the hidden `.streamlit` folder,
then deploy `app.py` from https://share.streamlit.io/.

## Important
This is still a prototype. The grading scale is generic/demo, not an official board or university policy.
SQLite persistence on free hosting may not survive all restarts/redeployments. Do not use real student
records until persistent database storage, HTTPS, backup, account recovery, access-control review,
privacy review, and security testing are in place. Use fictional data while testing.
