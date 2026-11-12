import streamlit as st
import sqlite3
import hashlib
import secrets
import pandas as pd
from datetime import datetime
from pathlib import Path
from io import BytesIO

st.set_page_config(page_title="EduNexus 2.0", page_icon="🎓", layout="wide")
DB_PATH = Path("edunexus.db")

# ---------------- Database (compatible with V1) ----------------
def db():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

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

# ---------------- Authentication ----------------
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
        con.execute("INSERT INTO users(username,password_hash,salt,role,created_at) VALUES(?,?,?,?,?)",
                    (username.strip(), ph, salt, role, datetime.now().isoformat(timespec="seconds")))

def authenticate(username, password):
    with db() as con:
        row = con.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
    if row and verify_password(password, row["password_hash"], row["salt"]):
        return {"username": row["username"], "role": row["role"]}
    return None

# ---------------- Academic rules ----------------
def grade_for_percent(percent):
    # Generic configurable-style default. Confirm official institutional rules before real use.
    if percent >= 80: return "A+", 5.00
    if percent >= 70: return "A", 4.00
    if percent >= 60: return "A-", 3.50
    if percent >= 50: return "B", 3.00
    if percent >= 40: return "C", 2.00
    if percent >= 33: return "D", 1.00
    return "F", 0.00

def subject_rows(df):
    rows = []
    for r in df.itertuples():
        pct = (float(r.marks) / float(r.max_marks) * 100) if r.max_marks else 0
        grade, gp = grade_for_percent(pct)
        rows.append({"Subject": r.subject, "Marks": r.marks, "Out of": r.max_marks,
                     "Percentage": round(pct, 2), "Grade": grade, "Grade Point": gp,
                     "Status": "Pass" if gp > 0 else "Fail"})
    return pd.DataFrame(rows)

def summarize_exam(df):
    if df.empty:
        return None
    details = subject_rows(df)
    total = float(df["marks"].sum())
    maximum = float(df["max_marks"].sum())
    pct = (total / maximum * 100) if maximum else 0
    # Average subject grade points; any failed subject makes overall status Fail.
    gpa = round(float(details["Grade Point"].mean()), 2) if len(details) else 0
    gpa = min(gpa, 5.0)
    failed = int((details["Status"] == "Fail").sum())
    status = "Fail" if failed else "Pass"
    overall_grade, _ = grade_for_percent(pct)
    return {"total": total, "maximum": maximum, "percent": pct, "gpa": gpa,
            "grade": overall_grade, "status": status, "failed": failed, "details": details}

def students_df():
    with db() as con:
        return pd.read_sql_query("SELECT * FROM students ORDER BY full_name", con)

def all_results_df():
    with db() as con:
        return pd.read_sql_query("""
            SELECT r.*, s.full_name, s.roll, s.institution_type, s.institution_name,
                   s.department, s.class_name, s.section, s.academic_year, s.username
            FROM results r JOIN students s ON s.id=r.student_id
        """, con)

def result_for(student_id, exam):
    with db() as con:
        return pd.read_sql_query("SELECT exam_name,subject,marks,max_marks FROM results WHERE student_id=? AND exam_name=? ORDER BY subject",
                                 con, params=(int(student_id), exam))

def get_student(username):
    with db() as con:
        return con.execute("SELECT * FROM students WHERE username=?", (username,)).fetchone()

def make_marksheet_pdf(student, exam, summary):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("EduNexus — Academic Marksheet", styles["Title"]),
        Spacer(1, 8),
        Paragraph(f"<b>Institution:</b> {student['institution_name']}", styles["Normal"]),
        Paragraph(f"<b>Student:</b> {student['full_name']} &nbsp;&nbsp; <b>Roll:</b> {student['roll']}", styles["Normal"]),
        Paragraph(f"<b>Level:</b> {student['institution_type']} &nbsp;&nbsp; <b>Class/Year:</b> {student['class_name']}", styles["Normal"]),
        Paragraph(f"<b>Academic Year:</b> {student['academic_year']} &nbsp;&nbsp; <b>Exam:</b> {exam}", styles["Normal"]),
        Spacer(1, 12)
    ]
    data = [["Subject", "Marks", "Out of", "%", "Grade", "GP"]]
    for _, r in summary["details"].iterrows():
        data.append([str(r["Subject"]), f"{r['Marks']:g}", f"{r['Out of']:g}",
                     f"{r['Percentage']:.2f}", str(r["Grade"]), f"{r['Grade Point']:.2f}"])
    table = Table(data, repeatRows=1, colWidths=[55*mm, 22*mm, 22*mm, 22*mm, 22*mm, 20*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#243B63")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F1F5F9")]),
        ("PADDING",(0,0),(-1,-1),7),
    ]))
    story += [table, Spacer(1, 14),
              Paragraph(f"<b>Total:</b> {summary['total']:g}/{summary['maximum']:g} &nbsp;&nbsp; <b>Percentage:</b> {summary['percent']:.2f}%", styles["Normal"]),
              Paragraph(f"<b>GPA:</b> {summary['gpa']:.2f}/5.00 &nbsp;&nbsp; <b>Status:</b> {summary['status']}", styles["Normal"]),
              Spacer(1, 22),
              Paragraph("Generated by EduNexus 2.0. Verify the grading policy with your institution.", styles["Italic"])]
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()

# ---------------- UI Theme ----------------
if "user" not in st.session_state:
    st.session_state.user = None
if "theme" not in st.session_state:
    st.session_state.theme = "Light"

with st.sidebar:
    st.markdown("# 🎓 EduNexus")
    st.caption("Smart Result Management • Version 2.0")
    theme = st.radio("Appearance", ["Light", "Dark"], horizontal=True,
                     index=0 if st.session_state.theme == "Light" else 1)
    st.session_state.theme = theme

if st.session_state.theme == "Dark":
    st.markdown("""<style>
    .stApp {background:#0b1220;color:#e5e7eb}
    [data-testid="stSidebar"] {background:#111827}
    [data-testid="stMetric"] {background:#182338;border:1px solid #26364f;padding:14px;border-radius:14px}
    div[data-testid="stDataFrame"] {border:1px solid #334155;border-radius:10px}
    </style>""", unsafe_allow_html=True)
else:
    st.markdown("""<style>
    .block-container{padding-top:1.5rem;padding-bottom:2rem}
    [data-testid="stMetric"]{background:#f1f5f9;border:1px solid #e2e8f0;padding:14px;border-radius:14px}
    div.stButton>button,div.stDownloadButton>button{border-radius:9px;font-weight:600}
    </style>""", unsafe_allow_html=True)

# ---------------- First admin setup ----------------
if user_count() == 0:
    st.title("🎓 EduNexus 2.0")
    st.subheader("Create your first administrator account")
    st.info("First launch only: create an Admin account. Keep the password private.")
    with st.form("first_admin"):
        username = st.text_input("Admin username")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        submit = st.form_submit_button("Create Admin", use_container_width=True)
    if submit:
        if not username.strip() or len(password) < 8:
            st.error("Enter a username and a password with at least 8 characters.")
        elif password != confirm:
            st.error("Passwords do not match.")
        else:
            try:
                add_user(username, password, "Admin")
                st.success("Admin account created. Log in now.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Username already exists.")
    st.stop()

# ---------------- Login ----------------
if st.session_state.user is None:
    st.title("🎓 EduNexus 2.0")
    st.subheader("Premium Academic Result Portal")
    left, right = st.columns([1.15, .85], gap="large")
    with left:
        st.markdown("### Welcome back")
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign in", use_container_width=True)
        if submit:
            u = authenticate(username, password)
            if u:
                st.session_state.user = u
                st.rerun()
            st.error("Invalid username or password.")
    with right:
        st.markdown("### One portal. Three roles.")
        st.markdown("🛡️ **Admin** — manage users, students and reports  \n🧑‍🏫 **Teacher** — enter marks and analyze results  \n🎓 **Student** — view personal marksheets")
        st.caption("Version 2.0 prototype. Use fictional data until production security is configured.")
    st.stop()

user = st.session_state.user
with st.sidebar:
    st.divider()
    st.write(f"**Signed in:** {user['username']}")
    st.write(f"**Role:** {user['role']}")
    if st.button("Log out", use_container_width=True):
        st.session_state.user = None
        st.rerun()

role = user["role"]
st.title("EduNexus")
st.caption("Premium Result Management & Academic Analytics")

sdf = students_df()
rdf = all_results_df()

# ---------------- Student view ----------------
if role == "Student":
    student = get_student(user["username"])
    st.subheader("My Results")
    if not student:
        st.warning("Your student profile is not linked. Contact your administrator.")
    else:
        st.markdown(f"### {student['full_name']}")
        st.caption(f"{student['institution_name']} • {student['institution_type']} • Roll {student['roll']}")
        with db() as con:
            exams = [x[0] for x in con.execute("SELECT DISTINCT exam_name FROM results WHERE student_id=? ORDER BY exam_name",
                                               (student["id"],)).fetchall()]
        if not exams:
            st.info("No published results yet.")
        else:
            exam = st.selectbox("Choose examination", exams)
            df = result_for(student["id"], exam)
            summary = summarize_exam(df)
            a,b,c,d = st.columns(4)
            a.metric("Total Marks", f"{summary['total']:g}/{summary['maximum']:g}")
            b.metric("Percentage", f"{summary['percent']:.2f}%")
            c.metric("GPA", f"{summary['gpa']:.2f}/5.00")
            d.metric("Result", summary["status"])
            st.dataframe(summary["details"], use_container_width=True, hide_index=True)
            st.download_button("⬇️ Download PDF Marksheet", make_marksheet_pdf(student, exam, summary),
                               file_name=f"marksheet_{student['roll']}_{exam.replace(' ','_')}.pdf",
                               mime="application/pdf", use_container_width=True)

# ---------------- Admin / Teacher ----------------
else:
    # Summary cards
    exam_count = rdf["exam_name"].nunique() if not rdf.empty else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Students", len(sdf))
    c2.metric("Result Entries", len(rdf))
    c3.metric("Examinations", exam_count)
    c4.metric("Subjects", rdf["subject"].nunique() if not rdf.empty else 0)

    tabs_list = ["Overview", "Students", "Enter Results", "Advanced Search", "Merit List"]
    if role == "Admin":
        tabs_list += ["User Management", "Export"]
    tabs = st.tabs(tabs_list)

    with tabs[0]:
        st.subheader("Academic Performance")
        if rdf.empty:
            st.info("Add students and enter marks to unlock analytics.")
        else:
            l,r = st.columns(2)
            with l:
                st.markdown("**Average marks by subject**")
                st.bar_chart(rdf.groupby("subject")["marks"].mean())
            with r:
                st.markdown("**Institution level distribution**")
                st.bar_chart(rdf.groupby("institution_type").size())
            st.markdown("**Recent result entries**")
            st.dataframe(rdf[["full_name","roll","exam_name","subject","marks","max_marks"]].tail(15),
                         use_container_width=True, hide_index=True)

    with tabs[1]:
        st.subheader("Student Directory")
        if role == "Admin":
            with st.expander("➕ Add student", expanded=False):
                with st.form("add_student"):
                    name = st.text_input("Full name")
                    roll = st.text_input("Roll / Student ID")
                    typ = st.selectbox("Institution type", ["School","College","University"])
                    inst = st.text_input("Institution name")
                    dept = st.text_input("Department / Group")
                    cls = st.text_input("Class / Year / Semester")
                    section = st.text_input("Section")
                    year = st.text_input("Academic year", value=str(datetime.now().year))
                    st.markdown("**Student login**")
                    su = st.text_input("Student username")
                    sp = st.text_input("Temporary password", type="password")
                    save = st.form_submit_button("Save student", use_container_width=True)
                if save:
                    if not all([name.strip(),roll.strip(),inst.strip(),year.strip(),su.strip()]) or len(sp)<8:
                        st.error("Complete required fields; password must be at least 8 characters.")
                    else:
                        try:
                            with db() as con:
                                con.execute("""INSERT INTO students(full_name,roll,institution_type,institution_name,
                                    department,class_name,section,academic_year,username,created_at)
                                    VALUES(?,?,?,?,?,?,?,?,?,?)""",
                                    (name.strip(),roll.strip(),typ,inst.strip(),dept,cls,section,year,su.strip(),
                                     datetime.now().isoformat(timespec="seconds")))
                            add_user(su,sp,"Student")
                            st.success("Student added.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Duplicate roll for institution/year or username.")
        if not sdf.empty:
            filters = st.text_input("Quick filter students by name, roll, class or institution")
            view = sdf.copy()
            if filters:
                mask = False
                for col in ["full_name","roll","class_name","institution_name","department"]:
                    mask = mask | view[col].astype(str).str.contains(filters, case=False, na=False)
                view = view[mask]
            st.dataframe(view[["full_name","roll","institution_type","institution_name","department","class_name","section","academic_year"]],
                         use_container_width=True, hide_index=True)
        else:
            st.info("No student records yet.")

    with tabs[2]:
        st.subheader("Enter / Update Subject Marks")
        if sdf.empty:
            st.warning("Add students first.")
        else:
            opts = {f"{r.full_name} | Roll {r.roll} | {r.institution_name}": int(r.id) for r in sdf.itertuples()}
            with st.form("marks_form"):
                chosen = st.selectbox("Student", list(opts.keys()))
                exam = st.text_input("Examination name", placeholder="Final Examination 2026")
                subject = st.text_input("Subject")
                x,y = st.columns(2)
                marks = x.number_input("Obtained marks", min_value=0.0, value=0.0, step=1.0)
                maximum = y.number_input("Maximum marks", min_value=1.0, value=100.0, step=1.0)
                save = st.form_submit_button("Save marks", use_container_width=True)
            if save:
                if not exam.strip() or not subject.strip():
                    st.error("Exam and subject are required.")
                elif marks > maximum:
                    st.error("Obtained marks cannot exceed maximum marks.")
                else:
                    with db() as con:
                        con.execute("""INSERT INTO results(student_id,exam_name,subject,marks,max_marks,entered_by,created_at)
                            VALUES(?,?,?,?,?,?,?) ON CONFLICT(student_id,exam_name,subject)
                            DO UPDATE SET marks=excluded.marks,max_marks=excluded.max_marks,
                            entered_by=excluded.entered_by,created_at=excluded.created_at""",
                            (opts[chosen],exam.strip(),subject.strip(),marks,maximum,user["username"],
                             datetime.now().isoformat(timespec="seconds")))
                    st.success("Marks saved/updated.")
                    st.rerun()

    with tabs[3]:
        st.subheader("Advanced Result Search")
        if rdf.empty:
            st.info("No results available.")
        else:
            f1,f2,f3 = st.columns(3)
            q = f1.text_input("Student name / Roll")
            exam_values = ["All"] + sorted(rdf["exam_name"].dropna().unique().tolist())
            exam_filter = f2.selectbox("Examination", exam_values)
            level_values = ["All"] + sorted(rdf["institution_type"].dropna().unique().tolist())
            level_filter = f3.selectbox("Institution level", level_values)
            view = rdf.copy()
            if q:
                view = view[view["full_name"].str.contains(q,case=False,na=False) | view["roll"].astype(str).str.contains(q,case=False,na=False)]
            if exam_filter != "All": view = view[view["exam_name"] == exam_filter]
            if level_filter != "All": view = view[view["institution_type"] == level_filter]
            st.caption(f"{len(view)} matching subject result entries")
            st.dataframe(view[["full_name","roll","institution_type","class_name","exam_name","subject","marks","max_marks"]],
                         use_container_width=True, hide_index=True)

    with tabs[4]:
        st.subheader("Merit List & Ranking")
        if rdf.empty:
            st.info("Enter results to generate a merit list.")
        else:
            exam_list = sorted(rdf["exam_name"].dropna().unique().tolist())
            exam_pick = st.selectbox("Select examination for ranking", exam_list, key="merit_exam")
            eligible = rdf[rdf["exam_name"] == exam_pick]
            ranked = []
            for sid, group in eligible.groupby("student_id"):
                summ = summarize_exam(group[["exam_name","subject","marks","max_marks"]])
                first = group.iloc[0]
                ranked.append({"Student":first["full_name"],"Roll":first["roll"],
                               "Class / Year":first["class_name"],"Institution":first["institution_name"],
                               "Total":f"{summ['total']:g}/{summ['maximum']:g}",
                               "Percentage":round(summ["percent"],2),"GPA":summ["gpa"],"Status":summ["status"]})
            rank_df = pd.DataFrame(ranked)
            if not rank_df.empty:
                rank_df = rank_df.sort_values(["Status","GPA","Percentage"],ascending=[True,False,False]).reset_index(drop=True)
                rank_df.insert(0,"Rank",range(1,len(rank_df)+1))
                st.dataframe(rank_df,use_container_width=True,hide_index=True)
                st.download_button("⬇️ Download merit list CSV",rank_df.to_csv(index=False).encode("utf-8-sig"),
                                   file_name=f"merit_list_{exam_pick.replace(' ','_')}.csv",mime="text/csv")

    if role == "Admin":
        with tabs[5]:
            st.subheader("User Management")
            with st.form("teacher_create"):
                tu = st.text_input("Teacher username")
                tp = st.text_input("Temporary password",type="password")
                create = st.form_submit_button("Create Teacher")
            if create:
                if not tu.strip() or len(tp)<8:
                    st.error("Username required; password must be at least 8 characters.")
                else:
                    try:
                        add_user(tu,tp,"Teacher")
                        st.success("Teacher account created.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Username already exists.")
            with db() as con:
                users = pd.read_sql_query("SELECT username,role,created_at FROM users ORDER BY role,username",con)
            st.dataframe(users,use_container_width=True,hide_index=True)

        with tabs[6]:
            st.subheader("Export Reports")
            if rdf.empty:
                st.info("No results to export.")
            else:
                export = rdf[["full_name","roll","institution_type","institution_name","department",
                              "class_name","academic_year","exam_name","subject","marks","max_marks"]]
                st.download_button("⬇️ Export all results (CSV)",export.to_csv(index=False).encode("utf-8-sig"),
                                   file_name="edunexus_v2_results.csv",mime="text/csv",use_container_width=True)

st.divider()
st.caption("EduNexus 2.0 • Prototype • Confirm official grading rules and security requirements before real institutional use.")
