# EduNexus — Smart Result Management System

A beginner-friendly Streamlit + SQLite prototype for School, College and University result management.

## Run locally / in a Python environment

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown by Streamlit.

## First login

On first launch, the app asks you to create the first Admin account. Choose a unique username and a password of at least 8 characters.

## Roles

- Admin: add student records and student accounts, create teacher accounts, view dashboard, search results and export CSV.
- Teacher: view students, enter/update marks, search results.
- Student: view only the result linked to their student account.

## Important prototype notes

- This is a learning prototype, not production-ready software.
- The default grade scale is generic and must be changed to match the institution's official rules.
- SQLite is suitable for a local prototype. For a real multi-user institution, use a hosted database, HTTPS, stronger account recovery, audit logs, backups, rate limiting, and a proper deployment setup.
- Do not upload real student personal data or publish this app publicly until security and privacy controls have been reviewed.
- Streamlit Community Cloud's local filesystem should not be treated as durable database storage. Use a persistent hosted database for production.

## Suggested next steps

1. Add institution-specific grading rules.
2. Add class/department filters and exam management.
3. Add PDF report cards.
4. Add secure password reset and account administration.
5. Deploy with a persistent database.
