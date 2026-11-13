import streamlit as st
import sqlite3, hashlib, secrets, hmac, csv, io
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="EduNexus V4", page_icon="🎓", layout="wide")
DB = "edunexus_v4.db"

def db():
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, salt TEXT NOT NULL,
          role TEXT NOT NULL CHECK(role IN ('Admin','Teacher','Student')),
          student_id TEXT
        );
        CREATE TABLE IF NOT EXISTS students (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, class_name TEXT NOT NULL,
          section TEXT DEFAULT '', roll TEXT DEFAULT '', session TEXT DEFAULT '2026',
          guardian TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS subjects (
          id INTEGER PRIMARY KEY AUTOINCREMENT, class_name TEXT NOT NULL,
          subject_name TEXT NOT NULL, full_marks REAL DEFAULT 100,
          UNIQUE(class_name, subject_name)
        );
        CREATE TABLE IF NOT EXISTS exams (
          id INTEGER PRIMARY KEY AUTOINCREMENT, exam_name TEXT NOT NULL,
          session TEXT NOT NULL, exam_date TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS marks (
          id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL,
          exam_id INTEGER NOT NULL, subject_id INTEGER NOT NULL,
          marks REAL NOT NULL, UNIQUE(student_id, exam_id, subject_id)
        );
        CREATE TABLE IF NOT EXISTS announcements (
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
          body TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit (
          id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT, action TEXT,
          detail TEXT, created_at TEXT NOT NULL
        );
        """)

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 240000).hex()
    return digest, salt

def verify_password(password, digest, salt):
    check, _ = hash_password(password, salt)
    return hmac.compare_digest(check, digest)

def audit(actor, action, detail=""):
    with db() as c:
        c.execute("INSERT INTO audit(actor,action,detail,created_at) VALUES(?,?,?,?)",
                  (actor, action, detail, datetime.now().isoformat(timespec="seconds")))

def get_setting(key, default=""):
    with db() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default

def set_setting(key, value):
    with db() as c:
        c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (key, str(value)))

def grade(mark, full):
    pct = (float(mark) / float(full) * 100) if full else 0
    if pct >= 80: return "A+", 5.00
    if pct >= 70: return "A", 4.00
    if pct >= 60: return "A-", 3.50
    if pct >= 50: return "B", 3.00
    if pct >= 40: return "C", 2.00
    if pct >= 33: return "D", 1.00
    return "F", 0.00

init_db()
st.markdown("""
<style>
:root {
    color-scheme: light;
}
.stApp {
    background: linear-gradient(135deg, #F4F7FC 0%, #F8FAFF 58%, #EEF7F5 100%) !important;
    color: #172B4D !important;
}
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background: transparent !important;
}
[data-testid="stSidebar"] {
    background: #101D35 !important;
}
[data-testid="stSidebar"] * {
    color: #F4F7FF !important;
}
h1, h2, h3, h4, p, label, .stMarkdown, .stText,
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"] {
    color: #172B4D !important;
}
[data-testid="stMetric"] {
    background: #FFFFFF !important;
    color: #172B4D !important;
    padding: 18px 20px !important;
    border-radius: 16px !important;
    border: 1px solid #E1E8F2 !important;
    box-shadow: 0 5px 18px rgba(23, 43, 77, 0.05) !important;
}
[data-testid="stMetric"] * {
    color: #172B4D !important;
}
.stButton > button, .stFormSubmitButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
}
div[data-testid="stDataFrame"] {
    border: 1px solid #E1E8F2;
    border-radius: 12px;
    overflow: hidden;
}
[data-testid="stAlert"] {
    border-radius: 12px !important;
}
@media (max-width: 768px) {
    [data-testid="stMainBlockContainer"] {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1rem !important;
    }
    h1 {
        font-size: 1.65rem !important;
        line-height: 1.25 !important;
    }
    h2 {
        font-size: 1.3rem !important;
    }
    [data-testid="stMetric"] {
        padding: 12px !important;
        min-height: 108px;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.65rem !important;
    }
    .stButton > button, .stFormSubmitButton > button {
        width: 100%;
        min-height: 44px;
    }
    [data-testid="stDataFrame"] {
        overflow-x: auto !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.title("🎓 EduNexus V5.0")
st.caption("Premium Mobile-Responsive Academic Management • School • College • University")

if not get_setting("setup_complete"):
    st.subheader("প্রথম Admin অ্যাকাউন্ট তৈরি")
    st.info("প্রথমবার চালুর সময় একটি নিরাপদ Admin username ও password দিন।")
    with st.form("setup"):
        institution = st.text_input("প্রতিষ্ঠানের নাম", "My Institution")
        username = st.text_input("Admin username")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        ok = st.form_submit_button("Create Admin", type="primary")
    if ok:
        if not username.strip() or len(password) < 8:
            st.error("Username দিন এবং অন্তত ৮ অক্ষরের password ব্যবহার করুন।")
        elif password != confirm:
            st.error("দুটি password মেলেনি।")
        else:
            digest, salt = hash_password(password)
            with db() as c:
                c.execute("INSERT INTO users(username,password_hash,salt,role) VALUES(?,?,?,'Admin')",
                          (username.strip(), digest, salt))
            set_setting("institution", institution.strip() or "My Institution")
            set_setting("setup_complete", "1")
            st.success("Admin account তৈরি হয়েছে। পেজটি refresh করে login করুন।")
    st.stop()

if "user" not in st.session_state:
    st.subheader("Login")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", type="primary")
    if submit:
        with db() as c:
            user = c.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
        if user and verify_password(password, user["password_hash"], user["salt"]):
            st.session_state.user = dict(user)
            audit(username, "LOGIN")
            st.rerun()
        else:
            st.error("Username অথবা password সঠিক নয়।")
    st.stop()

user = st.session_state.user
role = user["role"]
st.sidebar.title("EduNexus")
st.sidebar.caption(get_setting("institution", "Institution"))
st.sidebar.write(f"**{user['username']}** · {role}")
if st.sidebar.button("Logout"):
    audit(user["username"], "LOGOUT")
    del st.session_state.user
    st.rerun()

if role == "Admin":
    menu = st.sidebar.radio("Navigation", ["Overview","Students","Subjects","Exams & Marks","Users","Announcements","Reports & Audit","Settings"])
elif role == "Teacher":
    menu = st.sidebar.radio("Navigation", ["Overview","Students","Exams & Marks","Announcements"])
else:
    menu = st.sidebar.radio("Navigation", ["My Results","Announcements"])

def students_df():
    with db() as c:
        return pd.read_sql_query("SELECT * FROM students ORDER BY class_name, roll", c)

def exams_df():
    with db() as c:
        return pd.read_sql_query("SELECT * FROM exams ORDER BY id DESC", c)

def subjects_df():
    with db() as c:
        return pd.read_sql_query("SELECT * FROM subjects ORDER BY class_name, subject_name", c)

def result_data(student_id=None, exam_id=None):
    q = """SELECT s.id,s.name,s.class_name,s.section,s.roll,e.exam_name,
                  sub.subject_name,sub.full_marks,m.marks
           FROM marks m JOIN students s ON s.id=m.student_id
           JOIN exams e ON e.id=m.exam_id JOIN subjects sub ON sub.id=m.subject_id WHERE 1=1"""
    args=[]
    if student_id: q += " AND s.id=?"; args.append(student_id)
    if exam_id: q += " AND e.id=?"; args.append(int(exam_id))
    with db() as c:
        return pd.read_sql_query(q, c, params=args)

if menu == "Overview":
    st.header("Academic Overview")
    sdf, subdf, edf = students_df(), subjects_df(), exams_df()
    a,b,c,d = st.columns(4)
    a.metric("Students", len(sdf)); b.metric("Subjects", len(subdf)); c.metric("Exams", len(edf))
    with db() as con: total_marks = con.execute("SELECT COUNT(*) FROM marks").fetchone()[0]
    d.metric("Marks records", total_marks)
    st.subheader("Recent announcements")
    with db() as con: news = pd.read_sql_query("SELECT title,body,created_at FROM announcements ORDER BY id DESC LIMIT 5", con)
    if news.empty: st.info("এখনো কোনো announcement নেই।")
    else: st.dataframe(news, use_container_width=True, hide_index=True)

elif menu == "Students":
    st.header("Student Directory")
    if role == "Admin":
        with st.expander("নতুন শিক্ষার্থী যোগ করুন", expanded=True):
            with st.form("add_student"):
                sid=st.text_input("Student ID (unique)")
                name=st.text_input("Full name")
                cls=st.text_input("Class / Department")
                section=st.text_input("Section / Semester")
                roll=st.text_input("Roll")
                session=st.text_input("Academic session","2026")
                guardian=st.text_input("Guardian name (optional)")
                add=st.form_submit_button("Save student")
            if add:
                try:
                    with db() as con:
                        con.execute("INSERT INTO students VALUES(?,?,?,?,?,?,?)",
                                    (sid.strip(),name.strip(),cls.strip(),section,roll,session,guardian))
                    audit(user["username"],"ADD_STUDENT",sid)
                    st.success("Student added.")
                except Exception as e: st.error(f"Save হয়নি: {e}")
        st.markdown("**Bulk import:** CSV columns: `id,name,class_name,section,roll,session,guardian`")
        up=st.file_uploader("Student CSV", type=["csv"])
        if up and st.button("Import student CSV"):
            frame=pd.read_csv(up).fillna("")
            required={"id","name","class_name"}
            if not required.issubset(frame.columns): st.error("Required columns missing.")
            else:
                with db() as con:
                    for _,r in frame.iterrows():
                        con.execute("""INSERT INTO students(id,name,class_name,section,roll,session,guardian)
                        VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,
                        class_name=excluded.class_name,section=excluded.section,roll=excluded.roll,
                        session=excluded.session,guardian=excluded.guardian""",
                        (str(r["id"]),str(r["name"]),str(r["class_name"]),str(r.get("section","")),
                         str(r.get("roll","")),str(r.get("session","2026")),str(r.get("guardian",""))))
                audit(user["username"],"IMPORT_STUDENTS",str(len(frame)))
                st.success(f"{len(frame)} rows imported.")
    df=students_df()
    search=st.text_input("Search by ID, name, class or roll")
    if search:
        df=df[df.astype(str).apply(lambda col: col.str.contains(search,case=False,na=False)).any(axis=1)]
    st.dataframe(df,use_container_width=True,hide_index=True)

elif menu == "Subjects":
    st.header("Subject Management")
    with st.form("subject_form"):
        cls=st.text_input("Class / Department")
        subject=st.text_input("Subject name")
        full=st.number_input("Full marks",min_value=1.0,value=100.0)
        save=st.form_submit_button("Add subject")
    if save:
        try:
            with db() as con: con.execute("INSERT INTO subjects(class_name,subject_name,full_marks) VALUES(?,?,?)",(cls,subject,full))
            audit(user["username"],"ADD_SUBJECT",f"{cls}/{subject}")
            st.success("Subject added.")
        except Exception as e: st.error(f"Save হয়নি: {e}")
    st.dataframe(subjects_df(),use_container_width=True,hide_index=True)

elif menu == "Exams & Marks":
    st.header("Exams & Marks")
    if role == "Admin":
        with st.expander("Create exam"):
            with st.form("exam_form"):
                en=st.text_input("Exam name")
                ses=st.text_input("Session","2026")
                date=st.text_input("Exam date (optional)")
                create=st.form_submit_button("Create exam")
            if create and en.strip():
                with db() as con: con.execute("INSERT INTO exams(exam_name,session,exam_date) VALUES(?,?,?)",(en,ses,date))
                audit(user["username"],"CREATE_EXAM",en); st.success("Exam created.")
    edf=exams_df(); sdf=students_df(); subdf=subjects_df()
    if edf.empty or sdf.empty or subdf.empty:
        st.info("Marks entry-এর আগে student, subject এবং exam তৈরি করুন।")
    else:
        exam_options={f"{r.exam_name} · {r.session}":int(r.id) for r in edf.itertuples()}
        exam_label=st.selectbox("Select exam",list(exam_options))
        student_options={f"{r.id} · {r.name} · {r.class_name}":r.id for r in sdf.itertuples()}
        student_label=st.selectbox("Select student",list(student_options))
        sid=student_options[student_label]
        stu=sdf[sdf.id==sid].iloc[0]
        eligible=subdf[subdf.class_name==stu.class_name]
        if eligible.empty: st.warning("এই শিক্ষার্থীর class-এর জন্য subject নেই।")
        else:
            with st.form("marks_form"):
                entries={}
                for r in eligible.itertuples():
                    entries[int(r.id)]=(r.subject_name,r.full_marks,st.number_input(
                        f"{r.subject_name} (out of {r.full_marks})",min_value=0.0,
                        max_value=float(r.full_marks),step=1.0,key=f"m_{sid}_{exam_options[exam_label]}_{r.id}"))
                save=st.form_submit_button("Save / Update marks",type="primary")
            if save:
                with db() as con:
                    for subid,(_,fullmark,mark) in entries.items():
                        con.execute("""INSERT INTO marks(student_id,exam_id,subject_id,marks) VALUES(?,?,?,?)
                        ON CONFLICT(student_id,exam_id,subject_id) DO UPDATE SET marks=excluded.marks""",
                        (sid,exam_options[exam_label],subid,mark))
                audit(user["username"],"SAVE_MARKS",f"{sid}/{exam_label}")
                st.success("Marks saved.")
    if not edf.empty:
        selected=st.selectbox("View marks for exam",["All"]+[f"{r.exam_name} · {r.session}" for r in edf.itertuples()])
        exid=None if selected=="All" else int(edf.iloc[[i for i,r in enumerate(edf.itertuples()) if f"{r.exam_name} · {r.session}"==selected][0]].id)
        st.dataframe(result_data(exam_id=exid),use_container_width=True,hide_index=True)

elif menu == "Users":
    st.header("User Accounts")
    with st.form("new_user"):
        username=st.text_input("Username")
        password=st.text_input("Temporary password (min 8)",type="password")
        user_role=st.selectbox("Role",["Admin","Teacher","Student"])
        student_id=st.text_input("Student ID (Student role only)")
        create=st.form_submit_button("Create account")
    if create:
        if len(password)<8: st.error("Password অন্তত ৮ অক্ষরের হতে হবে।")
        elif user_role=="Student" and not student_id: st.error("Student ID দিন।")
        else:
            digest,salt=hash_password(password)
            try:
                with db() as con: con.execute("INSERT INTO users(username,password_hash,salt,role,student_id) VALUES(?,?,?,?,?)",
                                               (username.strip(),digest,salt,user_role,student_id.strip() or None))
                audit(user["username"],"CREATE_USER",f"{username}/{user_role}"); st.success("Account created.")
            except Exception as e: st.error(f"Account তৈরি হয়নি: {e}")
    with db() as con: users=pd.read_sql_query("SELECT id,username,role,student_id FROM users",con)
    st.dataframe(users,use_container_width=True,hide_index=True)

elif menu == "My Results":
    st.header("My Academic Results")
    sid=user.get("student_id")
    if not sid: st.warning("এই account-এর সঙ্গে Student ID যুক্ত করা নেই। Admin-এর সঙ্গে যোগাযোগ করুন।")
    else:
        with db() as con: student=con.execute("SELECT * FROM students WHERE id=?",(sid,)).fetchone()
        if not student: st.warning("Student profile পাওয়া যায়নি।")
        else:
            st.subheader(student["name"])
            st.caption(f"ID: {sid} · Class: {student['class_name']} · Roll: {student['roll']}")
            df=result_data(student_id=sid)
            if df.empty: st.info("এখনো কোনো result প্রকাশিত হয়নি।")
            else:
                df["Grade"]=df.apply(lambda r: grade(r["marks"],r["full_marks"])[0],axis=1)
                st.dataframe(df[["exam_name","subject_name","marks","full_marks","Grade"]],use_container_width=True,hide_index=True)
                st.bar_chart(df.set_index("subject_name")["marks"])

elif menu == "Announcements":
    st.header("Announcements")
    if role=="Admin":
        with st.form("announcement"):
            title=st.text_input("Title")
            body=st.text_area("Message")
            publish=st.form_submit_button("Publish")
        if publish and title.strip() and body.strip():
            with db() as con: con.execute("INSERT INTO announcements(title,body,created_at) VALUES(?,?,?)",
                                          (title,body,datetime.now().isoformat(timespec="minutes")))
            audit(user["username"],"PUBLISH_ANNOUNCEMENT",title); st.success("Published.")
    with db() as con: posts=pd.read_sql_query("SELECT * FROM announcements ORDER BY id DESC",con)
    for p in posts.to_dict("records"):
        with st.container(border=True):
            st.subheader(p["title"]); st.write(p["body"]); st.caption(p["created_at"])

elif menu == "Reports & Audit":
    st.header("Reports & Audit Trail")
    df=result_data()
    if not df.empty:
        df["percentage"]=(df["marks"]/df["full_marks"]*100).round(1)
        st.metric("Average marks percentage",f"{df.percentage.mean():.1f}%")
        st.bar_chart(df.groupby("subject_name")["percentage"].mean())
        st.download_button("Download results CSV",df.to_csv(index=False).encode("utf-8-sig"),
                           "edunexus_results.csv","text/csv")
    with db() as con: logs=pd.read_sql_query("SELECT * FROM audit ORDER BY id DESC LIMIT 300",con)
    st.subheader("Recent activity")
    st.dataframe(logs,use_container_width=True,hide_index=True)

elif menu == "Settings":
    st.header("Institution Settings")
    institution=st.text_input("Institution name",get_setting("institution","My Institution"))
    if st.button("Save institution name"):
        set_setting("institution",institution.strip()); audit(user["username"],"UPDATE_SETTINGS",institution)
        st.success("Saved.")
    st.warning("এই সংস্করণে grading scale demo হিসেবে রাখা হয়েছে। বাস্তব প্রতিষ্ঠানের অনুমোদিত grading policy অনুযায়ী পরিবর্তন করতে হবে।")
    st.subheader("Backup reminder")
    st.write("SQLite database file: `edunexus_v4.db` — নিয়মিত নিরাপদ backup রাখুন।")
    st.error("এটি prototype। বাস্তব শিক্ষার্থীর তথ্য ব্যবহারের আগে hosting persistence, HTTPS, backup, account recovery, role permissions, audit review এবং security testing সম্পন্ন করুন।")
