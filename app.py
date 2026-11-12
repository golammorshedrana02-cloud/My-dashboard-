import streamlit as st
import sqlite3
import hashlib
import secrets
import pandas as pd
from datetime import datetime
from pathlib import Path

DB_PATH = Path("edunexus.db")

st.set_page_config(page_title="EduNexus | Result Portal", page_icon="🎓", layout="wide")

# ---------- Database ----------
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Admin','Teacher','Student')),
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            roll TEXT NOT NULL,
            institution_type TEXT NOT NULL,
            institution_name TEXT NOT NULL,
            department TEXT DEFAULT '',
            class_name TEXT DEFAULT '',
            section TEXT DEFAULT '',
            academic_year TEXT NOT NULL,
            username TEXT UNIQUE,
            created_at TEXT NOT NULL,
            UNIQUE(institution_name, academic_year, roll)
        );
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            exam_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            marks REAL NOT NULL,
            max_marks REAL NOT NULL,
            entered_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(student_id, exam_name, subject),
            FOREIGN KEY(student_id) REFERENCES students(id)
        );
        """)
init_db()

# ---------- Authentication ----------
def make_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 180_000).hex()
    return digest, salt

def verify_password(password, stored_hash, salt):
    return secrets.compare_digest(make_password(password, salt)[0], stored_hash)

def user_count():
    with db() as con:
        return con.execute("SELECT COUNT(*) FROM users").fetchone()[0]

def add_user(username, password, role):
    ph, salt = make_password(password)
    with db() as con:
        con.execute(
            "INSERT INTO users(username,password_hash,salt,role,created_at) VALUES(?,?,?,?,?)",
            (username.strip(), ph, salt, role, datetime.now().isoformat(timespec="seconds"))
        )

def authenticate(username, password):
    with db() as con:
        row = con.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
    if row and verify_password(password, row["password_hash"], row["salt"]):
        return {"username": row["username"], "role": row["role"]}
    return None

# ---------- Result helpers ----------
def grade_for(percent):
    # Generic default grading scale. Institutions can change this policy.
    if percent >= 80: return "A+", 5.00
    if percent >= 70: return "A", 4.00
    if percent >= 60: return "A-", 3.50
    if percent >= 50: return "B", 3.00
    if percent >= 40: return "C", 2.00
    if percent >= 33: return "D", 1.00
    return "F", 0.00

def student_result_frame(student_id, exam_name=None):
    query = """SELECT exam_name, subject, marks, max_marks
               FROM results WHERE student_id=?"""
    params = [student_id]
    if exam_name:
        query += " AND exam_name=?"
        params.append(exam_name)
    query += " ORDER BY exam_name, subject"
    with db() as con:
        rows = con.execute(query, params).fetchall()
    return pd.DataFrame([dict(r) for r in rows])

def result_summary(df):
    if df.empty:
        return None
    total = float(df["marks"].sum())
    maximum = float(df["max_marks"].sum())
    percent = (total / maximum * 100) if maximum else 0
    grade, gpa = grade_for(percent)
    return {"total": total, "maximum": maximum, "percent": percent, "grade": grade, "gpa": gpa,
            "status": "Pass" if grade != "F" else "Fail"}

def all_students():
    with db() as con:
        return pd.read_sql_query("SELECT * FROM students ORDER BY full_name", con)

def get_student_by_username(username):
    with db() as con:
        return con.execute("SELECT * FROM students WHERE username=?", (username,)).fetchone()

def sidebar_user():
    st.sidebar.markdown("## 🎓 EduNexus")
    st.sidebar.caption("Smart Result Management")
    st.sidebar.divider()
    st.sidebar.write(f"**User:** {st.session_state.user['username']}")
    st.sidebar.write(f"**Role:** {st.session_state.user['role']}")
    if st.sidebar.button("Log out", use_container_width=True):
        st.session_state.user = None
        st.rerun()

# ---------- First-run setup ----------
if "user" not in st.session_state:
    st.session_state.user = None

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {background: rgba(100,116,139,.08); padding: 14px; border-radius: 12px;}
div.stButton > button {border-radius: 9px; font-weight: 600;}
</style>
""", unsafe_allow_html=True)

if user_count() == 0:
    st.title("🎓 EduNexus")
    st.subheader("Create your first administrator account")
    st.info("First-time setup: create an Admin login. Keep these credentials private.")
    with st.form("first_admin"):
        username = st.text_input("Admin username", placeholder="e.g. admin")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create Admin", use_container_width=True)
    if submitted:
        if not username.strip() or len(password) < 8:
            st.error("Enter a username and a password with at least 8 characters.")
        elif password != confirm:
            st.error("Passwords do not match.")
        else:
            try:
                add_user(username, password, "Admin")
                st.success("Admin created. Please log in.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("That username is already in use.")
    st.stop()

# ---------- Login ----------
if st.session_state.user is None:
    st.title("🎓 EduNexus")
    st.subheader("School • College • University Result Portal")
    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        st.markdown("### Welcome back")
        st.write("Sign in to manage academic records or view student results.")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
        if submit:
            user = authenticate(username, password)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Incorrect username or password.")
    with right:
        st.markdown("### Portal access")
        st.markdown("- 🛡️ **Admin:** users, students and full reports\n- 🧑‍🏫 **Teacher:** student records and results\n- 🎓 **Student:** personal academic results")
        st.caption("Demo application. Do not enter real student data until securely deployed.")
    st.stop()

user = st.session_state.user
sidebar_user()
role = user["role"]

# ---------- Admin / Teacher shared dashboard ----------
st.title("EduNexus Dashboard")
st.caption("Academic performance overview")

students_df = all_students()
with db() as con:
    results_df = pd.read_sql_query("""
        SELECT r.*, s.full_name, s.roll, s.institution_type, s.institution_name,
               s.class_name, s.academic_year
        FROM results r JOIN students s ON s.id=r.student_id
    """, con)

if role in ("Admin", "Teacher"):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Students", len(students_df))
    c2.metric("Result Entries", len(results_df))
    if not results_df.empty:
        passed = 0
        for sid, group in results_df.groupby(["student_id", "exam_name"]):
            summary = result_summary(group)
            passed += int(summary["status"] == "Pass")
        total_exams = results_df.groupby(["student_id", "exam_name"]).ngroups
        c3.metric("Pass Rate", f"{(passed/total_exams*100):.1f}%" if total_exams else "—")
        c4.metric("Average Marks", f"{results_df['marks'].mean():.1f}")
    else:
        c3.metric("Pass Rate", "—")
        c4.metric("Average Marks", "—")

    tab_names = ["Overview", "Students", "Enter Results", "Result Search"]
    if role == "Admin":
        tab_names += ["User Management", "Export"]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        st.subheader("Performance analytics")
        if results_df.empty:
            st.info("No results yet. Add students and enter results to see analytics.")
        else:
            chart_data = results_df.groupby("subject", as_index=False)["marks"].mean()
            st.markdown("**Average marks by subject**")
            st.bar_chart(chart_data.set_index("subject"))
            st.markdown("**Recent result records**")
            st.dataframe(results_df[["full_name","roll","exam_name","subject","marks","max_marks"]].tail(20),
                         use_container_width=True, hide_index=True)

    with tabs[1]:
        st.subheader("Student directory")
        if role == "Admin":
            with st.expander("➕ Add student and student login", expanded=False):
                with st.form("add_student"):
                    name = st.text_input("Full name")
                    roll = st.text_input("Roll / Student ID")
                    inst_type = st.selectbox("Institution type", ["School","College","University"])
                    inst_name = st.text_input("Institution name")
                    a, b = st.columns(2)
                    dept = a.text_input("Department / Group")
                    class_name = b.text_input("Class / Year / Semester")
                    section = st.text_input("Section (optional)")
                    year = st.text_input("Academic year", value=str(datetime.now().year))
                    st.markdown("**Student login credentials**")
                    su = st.text_input("Student username")
                    sp = st.text_input("Temporary password", type="password")
                    add = st.form_submit_button("Save student", use_container_width=True)
                if add:
                    if not all([name.strip(), roll.strip(), inst_name.strip(), year.strip(), su.strip()]) or len(sp) < 8:
                        st.error("Complete required fields. Password must be at least 8 characters.")
                    else:
                        try:
                            with db() as con:
                                con.execute("""INSERT INTO students(full_name,roll,institution_type,institution_name,
                                    department,class_name,section,academic_year,username,created_at)
                                    VALUES(?,?,?,?,?,?,?,?,?,?)""",
                                    (name.strip(),roll.strip(),inst_type,inst_name.strip(),dept,class_name,section,year,su.strip(),
                                     datetime.now().isoformat(timespec="seconds")))
                            add_user(su, sp, "Student")
                            st.success("Student record and login created.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Duplicate roll for this institution/year, or username already exists.")
        if not students_df.empty:
            st.dataframe(students_df[["full_name","roll","institution_type","institution_name","class_name","academic_year","username"]],
                         use_container_width=True, hide_index=True)
        else:
            st.info("No students added yet.")

    with tabs[2]:
        st.subheader("Enter or update marks")
        if students_df.empty:
            st.warning("Add students first.")
        else:
            student_options = {f"{r.full_name} | Roll: {r.roll} | {r.institution_name}": int(r.id)
                               for r in students_df.itertuples()}
            with st.form("enter_result"):
                chosen = st.selectbox("Student", list(student_options.keys()))
                exam = st.text_input("Exam name", placeholder="e.g. Half-Yearly 2026")
                subject = st.text_input("Subject", placeholder="e.g. Mathematics")
                a, b = st.columns(2)
                marks = a.number_input("Obtained marks", min_value=0.0, value=0.0, step=1.0)
                maximum = b.number_input("Maximum marks", min_value=1.0, value=100.0, step=1.0)
                save = st.form_submit_button("Save result", use_container_width=True)
            if save:
                if not exam.strip() or not subject.strip():
                    st.error("Exam name and subject are required.")
                elif marks > maximum:
                    st.error("Obtained marks cannot exceed maximum marks.")
                else:
                    try:
                        with db() as con:
                            con.execute("""INSERT INTO results(student_id,exam_name,subject,marks,max_marks,entered_by,created_at)
                                VALUES(?,?,?,?,?,?,?) ON CONFLICT(student_id,exam_name,subject)
                                DO UPDATE SET marks=excluded.marks,max_marks=excluded.max_marks,
                                entered_by=excluded.entered_by,created_at=excluded.created_at""",
                                (student_options[chosen],exam.strip(),subject.strip(),marks,maximum,user["username"],
                                 datetime.now().isoformat(timespec="seconds")))
                        st.success("Result saved.")
                        st.rerun()
                    except sqlite3.Error as e:
                        st.error(f"Could not save result: {e}")

    with tabs[3]:
        st.subheader("Search student result")
        if students_df.empty:
            st.info("No student records available.")
        else:
            search = st.text_input("Search by student name or roll")
            filtered = students_df[
                students_df["full_name"].str.contains(search, case=False, na=False) |
                students_df["roll"].str.contains(search, case=False, na=False)
            ] if search else students_df
            if not filtered.empty:
                selected = st.selectbox("Select student", filtered["id"].tolist(),
                    format_func=lambda x: f"{filtered.loc[filtered.id==x,'full_name'].iloc[0]} — Roll {filtered.loc[filtered.id==x,'roll'].iloc[0]}")
                with db() as con:
                    exams = [r[0] for r in con.execute("SELECT DISTINCT exam_name FROM results WHERE student_id=? ORDER BY exam_name",(int(selected),)).fetchall()]
                if exams:
                    exam_pick = st.selectbox("Exam", exams)
                    df = student_result_frame(int(selected), exam_pick)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    summary = result_summary(df)
                    if summary:
                        x1,x2,x3,x4 = st.columns(4)
                        x1.metric("Total", f"{summary['total']:g}/{summary['maximum']:g}")
                        x2.metric("Percentage", f"{summary['percent']:.2f}%")
                        x3.metric("Grade", summary["grade"])
                        x4.metric("Status", summary["status"])
                else:
                    st.info("No results for this student yet.")
            else:
                st.info("No matching student found.")

    if role == "Admin":
        with tabs[4]:
            st.subheader("Create teacher accounts")
            with st.form("create_teacher"):
                tu = st.text_input("Teacher username")
                tp = st.text_input("Temporary password", type="password")
                create = st.form_submit_button("Create teacher")
            if create:
                if not tu.strip() or len(tp) < 8:
                    st.error("Enter username and a password of at least 8 characters.")
                else:
                    try:
                        add_user(tu, tp, "Teacher")
                        st.success("Teacher account created.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Username already exists.")
            with db() as con:
                users_df = pd.read_sql_query("SELECT username,role,created_at FROM users ORDER BY role,username", con)
            st.dataframe(users_df, use_container_width=True, hide_index=True)

        with tabs[5]:
            st.subheader("Export result data")
            if results_df.empty:
                st.info("No result data to export.")
            else:
                export_df = results_df[["full_name","roll","institution_type","institution_name",
                                        "class_name","academic_year","exam_name","subject","marks","max_marks"]]
                st.download_button("⬇️ Download results as CSV",
                    data=export_df.to_csv(index=False).encode("utf-8-sig"),
                    file_name="edunexus_results.csv", mime="text/csv", use_container_width=True)

# ---------- Student portal ----------
elif role == "Student":
    st.subheader("My academic results")
    student = get_student_by_username(user["username"])
    if not student:
        st.error("No student profile is linked to this account. Contact the administrator.")
    else:
        st.write(f"**{student['full_name']}**  |  Roll: **{student['roll']}**")
        st.caption(f"{student['institution_name']} • {student['institution_type']} • {student['academic_year']}")
        df = student_result_frame(student["id"])
        if df.empty:
            st.info("Your results have not been published yet.")
        else:
            exams = sorted(df["exam_name"].unique().tolist())
            selected_exam = st.selectbox("Select examination", exams)
            exam_df = df[df["exam_name"] == selected_exam]
            st.dataframe(exam_df[["subject","marks","max_marks"]], use_container_width=True, hide_index=True)
            summary = result_summary(exam_df)
            if summary:
                a,b,c,d = st.columns(4)
                a.metric("Total Marks", f"{summary['total']:g}/{summary['maximum']:g}")
                b.metric("Percentage", f"{summary['percent']:.2f}%")
                c.metric("Grade", summary["grade"])
                d.metric("Result", summary["status"])
            st.caption("Grade scale is a generic demo scale; institutions should configure their official grading rules.")
