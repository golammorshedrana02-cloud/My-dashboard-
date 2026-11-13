import streamlit as st
import sqlite3, hashlib, secrets, hmac, html
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="EduNexus V7.1", page_icon="🎓", layout="wide")
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
          guardian TEXT DEFAULT '', group_name TEXT DEFAULT 'Unassigned'
        );
        CREATE TABLE IF NOT EXISTS subjects (
          id INTEGER PRIMARY KEY AUTOINCREMENT, class_name TEXT NOT NULL,
          subject_name TEXT NOT NULL, full_marks REAL DEFAULT 100,
          group_name TEXT DEFAULT 'Common',
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
        CREATE TABLE IF NOT EXISTS attendance (
          id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL,
          attendance_date TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('Present','Absent','Late')),
          marked_by TEXT NOT NULL,
          UNIQUE(student_id, attendance_date)
        );
        """)
        # Safe migrations for databases created by earlier versions.
        for table, column, definition in [
            ("exams", "is_published", "INTEGER NOT NULL DEFAULT 0"),
            ("students", "group_name", "TEXT DEFAULT 'Unassigned'"),
            ("subjects", "group_name", "TEXT DEFAULT 'Common'")
        ]:
            cols = [r["name"] for r in c.execute(f"PRAGMA table_info({table})").fetchall()]
            if column not in cols:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

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
        c.execute("""INSERT INTO settings(key,value) VALUES(?,?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value""", (key, str(value)))

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
.stApp {background:linear-gradient(135deg,#F4F7FC 0%,#F8FAFF 58%,#EEF7F5 100%);color:#172B4D}
[data-testid="stSidebar"] {background:#101D35}
[data-testid="stSidebar"] * {color:#F4F7FF}
h1,h2,h3,h4,p,label,.stMarkdown,.stText {color:#172B4D}
[data-testid="stMetric"] {background:white;padding:16px;border-radius:15px;border:1px solid #E1E8F2}
.stButton>button,.stFormSubmitButton>button {border-radius:10px;font-weight:600;min-height:42px}
.announcement-card {background:white;border:1px solid #DCE5F0;border-left:5px solid #4263EB;border-radius:14px;padding:16px;margin:10px 0;color:#172B4D}
.announcement-card h4 {color:#172B4D;margin:0 0 8px}
.announcement-card p {color:#334155;margin:0 0 8px}
.announcement-card small {color:#64748B}
@media(max-width:768px){
 [data-testid="stMainBlockContainer"]{padding:1rem!important}
 h1{font-size:1.65rem!important}
 [data-testid="stMetric"]{padding:12px;min-height:95px}
}
</style>
""", unsafe_allow_html=True)

st.title("🎓 EduNexus V7.1")
st.caption("Smart Academic Suite • Science • Humanities • Business Studies • Results • Attendance")

if not get_setting("setup_complete"):
    st.subheader("প্রথম Admin অ্যাকাউন্ট তৈরি")
    st.info("প্রথমবার চালুর সময় একটি Admin username ও password তৈরি করুন।")
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
            st.success("Admin account তৈরি হয়েছে। এখন Login করুন।")
    st.stop()

if "user" not in st.session_state:
    st.subheader("Login")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", type="primary")
    if submit:
        with db() as c:
            user_row = c.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
        if user_row and verify_password(password, user_row["password_hash"], user_row["salt"]):
            st.session_state.user = dict(user_row)
            audit(username, "LOGIN")
            st.rerun()
        else:
            st.error("Username অথবা password সঠিক নয়।")
    st.stop()

user = st.session_state.user
role = user["role"]
st.sidebar.title("🎓 EduNexus")
st.sidebar.caption(get_setting("institution", "Institution"))
st.sidebar.write(f"**{user['username']}** · {role}")
if st.sidebar.button("Logout"):
    audit(user["username"], "LOGOUT")
    del st.session_state.user
    st.rerun()

if role == "Admin":
    pages = ["Overview","Students","Subjects","Exams & Marks","Attendance","Result Publishing","Users","Announcements","Reports & Audit","Settings"]
elif role == "Teacher":
    pages = ["Overview","Students","Subjects","Exams & Marks","Attendance","Announcements"]
else:
    pages = ["My Results","My Attendance","Announcements"]

st.markdown("### 📱 Main Navigation")
menu = st.selectbox("Choose Dashboard Section", pages, key="v71_navigation")

def students_df():
    with db() as c:
        return pd.read_sql_query("SELECT * FROM students ORDER BY class_name, roll", c)

def exams_df():
    with db() as c:
        return pd.read_sql_query("SELECT * FROM exams ORDER BY id DESC", c)

def subjects_df():
    with db() as c:
        return pd.read_sql_query("SELECT * FROM subjects ORDER BY group_name,class_name,subject_name", c)

def result_data(student_id=None, exam_id=None, published_only=False):
    q = """SELECT s.id,s.name,s.class_name,s.section,s.roll,s.group_name,e.exam_name,
                  e.is_published,sub.subject_name,sub.full_marks,m.marks
           FROM marks m JOIN students s ON s.id=m.student_id
           JOIN exams e ON e.id=m.exam_id JOIN subjects sub ON sub.id=m.subject_id WHERE 1=1"""
    args = []
    if student_id: q += " AND s.id=?"; args.append(student_id)
    if exam_id: q += " AND e.id=?"; args.append(int(exam_id))
    if published_only: q += " AND e.is_published=1"
    with db() as c:
        return pd.read_sql_query(q, c, params=args)

# HSC subject catalogue. Paper names are stored separately for marks entry.
GROUP_SUBJECTS = {
    "Science": [
        "Physics","Chemistry","Biology","Higher Mathematics",
        "Statistics","Geography","Agriculture Studies"
    ],
    "Humanities": [
        "Economics","Civics & Good Governance","Logic","History",
        "Islamic History & Culture","Social Work","Sociology",
        "Geography","Psychology","Agriculture Studies"
    ],
    "Business Studies": [
        "Accounting","Business Organization & Management",
        "Finance, Banking & Insurance","Production Management & Marketing",
        "Economics","Statistics"
    ]
}
COMMON_SUBJECTS = {
    "Bangla": ["1st Paper","2nd Paper"],
    "English": ["1st Paper","2nd Paper"],
    "ICT": ["Single Paper"]
}

if menu == "Overview":
    st.header("Academic Overview")
    sdf, subdf, edf = students_df(), subjects_df(), exams_df()
    a,b,c,d = st.columns(4)
    a.metric("Students", len(sdf)); b.metric("Subject Papers", len(subdf)); c.metric("Exams", len(edf))
    with db() as con:
        total_marks = con.execute("SELECT COUNT(*) FROM marks").fetchone()[0]
        attendance_today = con.execute("SELECT COUNT(*) FROM attendance WHERE attendance_date=?",
                                       (datetime.now().date().isoformat(),)).fetchone()[0]
    d.metric("Marks records", total_marks)
    st.metric("Attendance records today", attendance_today)
    st.subheader("Recent announcements")
    with db() as con:
        news = pd.read_sql_query("SELECT title,body,created_at FROM announcements ORDER BY id DESC LIMIT 5", con)
    if news.empty: st.info("এখনো কোনো announcement নেই।")
    else: st.dataframe(news, use_container_width=True, hide_index=True)

elif menu == "Students":
    st.header("Student Directory")
    if role == "Admin":
        with st.expander("নতুন শিক্ষার্থী যোগ করুন", expanded=True):
            with st.form("add_student"):
                sid = st.text_input("Student ID (unique)")
                name = st.text_input("Full name")
                cls = st.text_input("Class / Department")
                group_name = st.selectbox("Division / Group", ["Science","Humanities","Business Studies","Unassigned"])
                section = st.text_input("Section / Semester")
                roll = st.text_input("Roll")
                session = st.text_input("Academic session","2026")
                guardian = st.text_input("Guardian name (optional)")
                add = st.form_submit_button("Save student")
            if add:
                if not sid.strip() or not name.strip() or not cls.strip():
                    st.error("Student ID, Name ও Class আবশ্যক।")
                else:
                    try:
                        with db() as con:
                            con.execute("""INSERT INTO students
                            (id,name,class_name,section,roll,session,guardian,group_name)
                            VALUES(?,?,?,?,?,?,?,?)""",
                            (sid.strip(),name.strip(),cls.strip(),section,roll,session,guardian,group_name))
                        audit(user["username"],"ADD_STUDENT",sid)
                        st.success("Student added.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("এই Student ID আগে থেকেই আছে।")
        st.markdown("**Bulk import:** CSV columns: `id,name,class_name,section,roll,session,guardian,group_name`")
        up = st.file_uploader("Student CSV", type=["csv"])
        if up and st.button("Import student CSV"):
            frame = pd.read_csv(up).fillna("")
            required = {"id","name","class_name"}
            if not required.issubset(frame.columns):
                st.error("Required columns: id, name, class_name")
            else:
                with db() as con:
                    for _,r in frame.iterrows():
                        con.execute("""INSERT INTO students
                        (id,name,class_name,section,roll,session,guardian,group_name)
                        VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,class_name=excluded.class_name,
                        section=excluded.section,roll=excluded.roll,
                        session=excluded.session,guardian=excluded.guardian,
                        group_name=excluded.group_name""",
                        (str(r["id"]),str(r["name"]),str(r["class_name"]),
                         str(r.get("section","")),str(r.get("roll","")),
                         str(r.get("session","2026")),str(r.get("guardian","")),
                         str(r.get("group_name","Unassigned"))))
                audit(user["username"],"IMPORT_STUDENTS",str(len(frame)))
                st.success(f"{len(frame)} rows imported.")
                st.rerun()
    df = students_df()
    search = st.text_input("Search by ID, name, class or roll")
    if search:
        df = df[df.astype(str).apply(lambda col: col.str.contains(search,case=False,na=False)).any(axis=1)]
    st.dataframe(df,use_container_width=True,hide_index=True)

elif menu == "Subjects":
    st.header("📚 Subject Management – V7.1")
    if role == "Admin":
        st.subheader("Add HSC Subjects by Division")
        with st.form("v71_subject_form"):
            cls = st.text_input("Class / Department", placeholder="HSC 1st Year")
            group = st.selectbox("Select Division", ["Science","Humanities","Business Studies"])
            chosen = st.multiselect("Select group subjects", GROUP_SUBJECTS[group],
                                    default=GROUP_SUBJECTS[group])
            include_common = st.checkbox("Include Common Subjects (Bangla, English, ICT)", value=True)
            full = st.number_input("Full marks per paper", min_value=1.0, value=100.0)
            save = st.form_submit_button("Add Selected Subjects", type="primary")
        if save:
            if not cls.strip():
                st.error("Class / Department লিখুন।")
            elif not chosen:
                st.error("কমপক্ষে একটি Group Subject নির্বাচন করুন।")
            else:
                records = []
                if include_common:
                    for subject, papers in COMMON_SUBJECTS.items():
                        for paper in papers:
                            records.append(("Common", f"{subject} - {paper}"))
                for subject in chosen:
                    records.append((group, f"{subject} - 1st Paper"))
                    records.append((group, f"{subject} - 2nd Paper"))
                added = 0
                with db() as con:
                    for category, subject_name in records:
                        cur = con.execute("""INSERT OR IGNORE INTO subjects
                        (class_name,subject_name,full_marks,group_name)
                        VALUES(?,?,?,?)""", (cls.strip(),subject_name,full,category))
                        added += cur.rowcount
                audit(user["username"],"V71_ADD_SUBJECTS",f"{cls}/{group}/{added}")
                st.success(f"{added}টি নতুন paper যুক্ত হয়েছে। আগে থাকা subject duplicate হবে না।")
                st.rerun()

        with st.expander("Add a custom subject"):
            with st.form("custom_subject"):
                custom_class = st.text_input("Class / Department", key="custom_class")
                custom_group = st.selectbox("Division", ["Science","Humanities","Business Studies","Common"], key="custom_group")
                custom_name = st.text_input("Subject / Paper name")
                custom_full = st.number_input("Full marks", min_value=1.0, value=100.0, key="custom_full")
                custom_save = st.form_submit_button("Add Custom Subject")
            if custom_save:
                if not custom_class.strip() or not custom_name.strip():
                    st.error("Class এবং Subject name আবশ্যক।")
                else:
                    try:
                        with db() as con:
                            con.execute("""INSERT INTO subjects(class_name,subject_name,full_marks,group_name)
                            VALUES(?,?,?,?)""", (custom_class.strip(),custom_name.strip(),custom_full,custom_group))
                        audit(user["username"],"ADD_CUSTOM_SUBJECT",custom_name)
                        st.success("Custom subject added.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("এই subject আগে থেকেই আছে।")
    st.divider()
    st.subheader("Subject Directory")
    df = subjects_df()
    if not df.empty:
        f1,f2 = st.columns(2)
        class_filter = f1.selectbox("Filter class", ["All"] + sorted(df["class_name"].dropna().unique().tolist()))
        group_filter = f2.selectbox("Filter division", ["All","Common","Science","Humanities","Business Studies"])
        if class_filter != "All": df = df[df["class_name"] == class_filter]
        if group_filter != "All": df = df[df["group_name"] == group_filter]
        st.metric("Total Subject Papers", len(df))
        st.dataframe(df[["class_name","group_name","subject_name","full_marks"]],
                     use_container_width=True,hide_index=True)
    else:
        st.info("এখনো কোনো Subject যোগ করা হয়নি।")

elif menu == "Exams & Marks":
    st.header("Exams & Marks")
    if role == "Admin":
        with st.expander("Create exam"):
            with st.form("exam_form"):
                en = st.text_input("Exam name")
                ses = st.text_input("Session","2026")
                date = st.text_input("Exam date (optional)")
                create = st.form_submit_button("Create exam")
            if create and en.strip():
                with db() as con:
                    con.execute("INSERT INTO exams(exam_name,session,exam_date) VALUES(?,?,?)",(en,ses,date))
                audit(user["username"],"CREATE_EXAM",en); st.success("Exam created."); st.rerun()
    edf, sdf, subdf = exams_df(), students_df(), subjects_df()
    if edf.empty or sdf.empty or subdf.empty:
        st.info("Marks entry-এর আগে student, subject এবং exam তৈরি করুন।")
    else:
        exam_options = {f"{r.exam_name} · {r.session}":int(r.id) for r in edf.itertuples()}
        exam_label = st.selectbox("Select exam",list(exam_options))
        student_options = {f"{r.id} · {r.name} · {r.class_name} · {r.group_name}":r.id for r in sdf.itertuples()}
        student_label = st.selectbox("Select student",list(student_options))
        sid = student_options[student_label]
        stu = sdf[sdf.id == sid].iloc[0]
        eligible = subdf[
            (subdf["class_name"] == stu["class_name"]) &
            (subdf["group_name"].isin([stu["group_name"],"Common"]))
        ]
        if stu["group_name"] == "Unassigned":
            st.warning("এই Student-এর Division নির্ধারিত হয়নি। Students পেজে Group নির্বাচন করুন।")
        elif eligible.empty:
            st.warning("এই শিক্ষার্থীর Class ও Division-এর জন্য Subject নেই।")
        else:
            with st.form("marks_form"):
                entries = {}
                for r in eligible.itertuples():
                    entries[int(r.id)] = (r.subject_name,r.full_marks,st.number_input(
                        f"{r.subject_name} (out of {r.full_marks})",
                        min_value=0.0,max_value=float(r.full_marks),step=1.0,
                        key=f"m_{sid}_{exam_options[exam_label]}_{r.id}"))
                save = st.form_submit_button("Save / Update marks",type="primary")
            if save:
                with db() as con:
                    for subid,(_,fullmark,mark) in entries.items():
                        con.execute("""INSERT INTO marks(student_id,exam_id,subject_id,marks)
                        VALUES(?,?,?,?) ON CONFLICT(student_id,exam_id,subject_id)
                        DO UPDATE SET marks=excluded.marks""",
                        (sid,exam_options[exam_label],subid,mark))
                audit(user["username"],"SAVE_MARKS",f"{sid}/{exam_label}")
                st.success("Marks saved."); st.rerun()
        selected = st.selectbox("View marks for exam",["All"]+[f"{r.exam_name} · {r.session}" for r in edf.itertuples()])
        exid = None if selected == "All" else exam_options[selected]
        st.dataframe(result_data(exam_id=exid),use_container_width=True,hide_index=True)

elif menu == "Attendance":
    st.header("Daily Attendance")
    sdf = students_df()
    if sdf.empty:
        st.info("Attendance নেওয়ার আগে Student যোগ করুন।")
    else:
        classes = sorted(sdf["class_name"].dropna().unique().tolist())
        chosen_class = st.selectbox("Class / Department",classes)
        class_students = sdf[sdf["class_name"] == chosen_class].copy()
        groups = sorted(class_students["group_name"].dropna().unique().tolist())
        chosen_group = st.selectbox("Division",groups)
        class_students = class_students[class_students["group_name"] == chosen_group]
        day = st.date_input("Attendance date",value=datetime.now().date())
        day_key = day.isoformat()
        with db() as con:
            existing = pd.read_sql_query("SELECT student_id,status FROM attendance WHERE attendance_date=?",con,params=[day_key])
        existing_map = dict(zip(existing["student_id"],existing["status"]))
        st.write(f"**Students in this group: {len(class_students)}**")
        with st.form("attendance_form"):
            statuses = {}
            for student in class_students.itertuples():
                label = f"{student.name} · ID {student.id} · Roll {student.roll}"
                statuses[student.id] = st.selectbox(label,["Present","Absent","Late"],
                    index=["Present","Absent","Late"].index(existing_map.get(student.id,"Present")),
                    key=f"att_{day_key}_{student.id}")
            save_attendance = st.form_submit_button("Save attendance",type="primary")
        if save_attendance:
            with db() as con:
                for student_id,status in statuses.items():
                    con.execute("""INSERT INTO attendance(student_id,attendance_date,status,marked_by)
                    VALUES(?,?,?,?) ON CONFLICT(student_id,attendance_date)
                    DO UPDATE SET status=excluded.status,marked_by=excluded.marked_by""",
                    (student_id,day_key,status,user["username"]))
            audit(user["username"],"SAVE_ATTENDANCE",f"{chosen_class}/{chosen_group}/{day_key}")
            st.success("Attendance saved."); st.rerun()
        with db() as con:
            history = pd.read_sql_query("""SELECT s.id,s.name,s.roll,s.group_name,a.attendance_date,a.status,a.marked_by
                FROM attendance a JOIN students s ON s.id=a.student_id
                WHERE s.class_name=? AND s.group_name=? ORDER BY a.attendance_date DESC,s.roll""",
                con,params=[chosen_class,chosen_group])
        st.subheader("Attendance history")
        st.dataframe(history,use_container_width=True,hide_index=True)
        if not history.empty:
            st.download_button("Download attendance CSV",history.to_csv(index=False).encode("utf-8-sig"),
                               "edunexus_attendance.csv","text/csv")

elif menu == "Result Publishing":
    st.header("Result Review & Publishing")
    edf = exams_df()
    if edf.empty:
        st.info("প্রথমে একটি Exam তৈরি করুন।")
    else:
        labels = {f"{r.exam_name} · {r.session} · {'Published' if int(r.is_published) else 'Draft'}":int(r.id) for r in edf.itertuples()}
        selected = st.selectbox("Select exam to review",list(labels))
        exam_id = labels[selected]
        df = result_data(exam_id=exam_id)
        if df.empty:
            st.warning("এই পরীক্ষার জন্য এখনো marks entry নেই।")
        else:
            df["percentage"] = (df["marks"]/df["full_marks"]*100).round(1)
            st.metric("Marks entries",len(df))
            st.dataframe(df[["id","name","class_name","group_name","roll","subject_name","marks","full_marks","percentage"]],
                         use_container_width=True,hide_index=True)
            current = int(edf.loc[edf["id"] == exam_id,"is_published"].iloc[0])
            if current:
                st.success("এই পরীক্ষার ফলাফল Published।")
                if st.button("Unpublish results"):
                    with db() as con: con.execute("UPDATE exams SET is_published=0 WHERE id=?",(exam_id,))
                    audit(user["username"],"UNPUBLISH_RESULTS",str(exam_id)); st.rerun()
            else:
                st.warning("এখনো Draft অবস্থায় আছে।")
                confirm = st.checkbox("আমি marks যাচাই করেছি এবং প্রকাশের অনুমোদন দিচ্ছি।")
                if st.button("Publish results",type="primary",disabled=not confirm):
                    with db() as con: con.execute("UPDATE exams SET is_published=1 WHERE id=?",(exam_id,))
                    audit(user["username"],"PUBLISH_RESULTS",str(exam_id)); st.rerun()

elif menu == "Users":
    st.header("User Accounts")
    with st.form("new_user"):
        username = st.text_input("Username")
        password = st.text_input("Temporary password (min 8)",type="password")
        user_role = st.selectbox("Role",["Admin","Teacher","Student"])
        student_id = st.text_input("Student ID (Student role only)")
        create = st.form_submit_button("Create account")
    if create:
        if len(password) < 8: st.error("Password অন্তত ৮ অক্ষরের হতে হবে।")
        elif user_role == "Student" and not student_id: st.error("Student ID দিন।")
        else:
            digest,salt = hash_password(password)
            try:
                with db() as con:
                    con.execute("INSERT INTO users(username,password_hash,salt,role,student_id) VALUES(?,?,?,?,?)",
                                (username.strip(),digest,salt,user_role,student_id.strip() or None))
                audit(user["username"],"CREATE_USER",f"{username}/{user_role}"); st.success("Account created."); st.rerun()
            except sqlite3.IntegrityError: st.error("এই username আগে থেকেই আছে।")
    with db() as con: users = pd.read_sql_query("SELECT id,username,role,student_id FROM users",con)
    st.dataframe(users,use_container_width=True,hide_index=True)

elif menu == "My Results":
    st.header("My Academic Results")
    sid = user.get("student_id")
    if not sid: st.warning("এই account-এর সঙ্গে Student ID যুক্ত নেই।")
    else:
        with db() as con: student = con.execute("SELECT * FROM students WHERE id=?",(sid,)).fetchone()
        if not student: st.warning("Student profile পাওয়া যায়নি।")
        else:
            st.subheader(student["name"])
            st.caption(f"ID: {sid} · Class: {student['class_name']} · Group: {student['group_name']} · Roll: {student['roll']}")
            df = result_data(student_id=sid,published_only=True)
            if df.empty: st.info("এখনো কোনো result প্রকাশিত হয়নি।")
            else:
                df["Grade"] = df.apply(lambda r:grade(r["marks"],r["full_marks"])[0],axis=1)
                st.dataframe(df[["exam_name","subject_name","marks","full_marks","Grade"]],
                             use_container_width=True,hide_index=True)
                st.bar_chart(df.set_index("subject_name")["marks"])

elif menu == "My Attendance":
    st.header("My Attendance")
    sid = user.get("student_id")
    if not sid: st.warning("এই account-এর সঙ্গে Student ID যুক্ত নেই।")
    else:
        with db() as con:
            att = pd.read_sql_query("SELECT attendance_date,status FROM attendance WHERE student_id=? ORDER BY attendance_date DESC",con,params=[sid])
        if att.empty: st.info("এখনো attendance record পাওয়া যায়নি।")
        else:
            total = len(att)
            present = int((att["status"] == "Present").sum())
            late = int((att["status"] == "Late").sum())
            absent = int((att["status"] == "Absent").sum())
            rate = round((present+late)/total*100,1)
            x1,x2,x3,x4 = st.columns(4)
            x1.metric("Attendance",f"{rate}%"); x2.metric("Present",present)
            x3.metric("Absent",absent); x4.metric("Late",late)
            st.dataframe(att,use_container_width=True,hide_index=True)
            st.download_button("Download my attendance",att.to_csv(index=False).encode("utf-8-sig"),
                               "my_attendance.csv","text/csv")

elif menu == "Announcements":
    st.header("Announcements")
    if role == "Admin":
        with st.form("announcement"):
            title = st.text_input("Title")
            body = st.text_area("Message")
            publish = st.form_submit_button("Publish")
        if publish and title.strip() and body.strip():
            with db() as con:
                con.execute("INSERT INTO announcements(title,body,created_at) VALUES(?,?,?)",
                            (title.strip(),body,datetime.now().isoformat(timespec="minutes")))
            audit(user["username"],"PUBLISH_ANNOUNCEMENT",title); st.success("Published."); st.rerun()
    with db() as con: posts = pd.read_sql_query("SELECT * FROM announcements ORDER BY id DESC",con)
    if posts.empty: st.info("এখনো কোনো announcement প্রকাশিত হয়নি।")
    for p in posts.to_dict("records"):
        safe_title = html.escape(str(p["title"]))
        safe_body = html.escape(str(p["body"])).replace("\n","<br>")
        safe_date = html.escape(str(p["created_at"]))
        st.markdown(f'<div class="announcement-card"><h4>{safe_title}</h4><p>{safe_body}</p><small>{safe_date}</small></div>',
                    unsafe_allow_html=True)

elif menu == "Reports & Audit":
    st.header("Reports & Audit Trail")
    df = result_data()
    if not df.empty:
        df["percentage"] = (df["marks"]/df["full_marks"]*100).round(1)
        st.metric("Average marks percentage",f"{df.percentage.mean():.1f}%")
        st.bar_chart(df.groupby("subject_name")["percentage"].mean())
        st.download_button("Download results CSV",df.to_csv(index=False).encode("utf-8-sig"),
                           "edunexus_results.csv","text/csv")
        st.subheader("Exam-wise Merit List")
        exam_names = sorted(df["exam_name"].dropna().unique().tolist())
        if exam_names:
            chosen_exam = st.selectbox("Choose exam for merit list",exam_names)
            part = df[df["exam_name"] == chosen_exam].copy()
            summary = part.groupby(["id","name","class_name","roll"],as_index=False).agg(
                obtained=("marks","sum"),total=("full_marks","sum"))
            summary["percentage"] = (summary["obtained"]/summary["total"]*100).round(2)
            summary = summary.sort_values(["percentage","obtained"],ascending=False)
            summary.insert(0,"Rank",range(1,len(summary)+1))
            st.dataframe(summary,use_container_width=True,hide_index=True)
    with db() as con: logs = pd.read_sql_query("SELECT * FROM audit ORDER BY id DESC LIMIT 300",con)
    st.subheader("Recent activity")
    st.dataframe(logs,use_container_width=True,hide_index=True)

elif menu == "Settings":
    st.header("Institution Settings")
    institution = st.text_input("Institution name",get_setting("institution","My Institution"))
    if st.button("Save institution name"):
        set_setting("institution",institution.strip())
        audit(user["username"],"UPDATE_SETTINGS",institution)
        st.success("Saved.")
    st.warning("Grading scale এখন demo হিসেবে রাখা হয়েছে। প্রতিষ্ঠানের অনুমোদিত grading policy অনুযায়ী যাচাই করুন।")
    st.subheader("Database Backup")
    st.write(f"SQLite database file: `{DB}`")
    st.info("নিয়মিত database backup রাখুন। Public deployment-এর আগে HTTPS, persistent storage, access control ও security testing নিশ্চিত করুন।")
