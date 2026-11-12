import streamlit as st
import sqlite3, hashlib, secrets
import pandas as pd
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="EduNexus V3", page_icon="🎓", layout="wide")
DB = Path("edunexus_v3.db")

def db():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, salt TEXT NOT NULL,
          role TEXT NOT NULL CHECK(role IN ('Admin','Teacher','Student')),
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS students(
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, roll TEXT NOT NULL,
          institution TEXT NOT NULL, level TEXT NOT NULL, class_name TEXT DEFAULT '',
          academic_year TEXT NOT NULL, username TEXT UNIQUE,
          UNIQUE(institution, academic_year, roll));
        CREATE TABLE IF NOT EXISTS marks(
          id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL,
          exam TEXT NOT NULL, subject TEXT NOT NULL, obtained REAL NOT NULL,
          total REAL NOT NULL, entered_by TEXT NOT NULL, created_at TEXT NOT NULL,
          UNIQUE(student_id, exam, subject),
          FOREIGN KEY(student_id) REFERENCES students(id));
        """)
init_db()

def hash_pw(pw, salt=None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200000).hex()
    return h, salt

def add_user(c, username, password, role):
    h, salt = hash_pw(password)
    c.execute("INSERT INTO users(username,password_hash,salt,role,created_at) VALUES(?,?,?,?,?)",
              (username.strip(), h, salt, role, datetime.now().isoformat(timespec="seconds")))

def verify(username, password):
    with db() as c:
        u = c.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
    if not u: return None
    h, _ = hash_pw(password, u["salt"])
    return {"username":u["username"],"role":u["role"]} if secrets.compare_digest(h,u["password_hash"]) else None

def grade(p):
    if p >= 80: return "A+",5.0
    if p >= 70: return "A",4.0
    if p >= 60: return "A-",3.5
    if p >= 50: return "B",3.0
    if p >= 40: return "C",2.0
    if p >= 33: return "D",1.0
    return "F",0.0

def analyze(df):
    if df.empty: return None, pd.DataFrame()
    rows=[]
    for _,r in df.iterrows():
        pct = 100*r.obtained/r.total if r.total else 0
        g,gp=grade(pct)
        rows.append({"Subject":r.subject,"Marks":r.obtained,"Out of":r.total,
                     "Percent":round(pct,2),"Grade":g,"GP":gp,
                     "Status":"Pass" if gp else "Fail"})
    details=pd.DataFrame(rows)
    maximum=float(df.total.sum()); obtained=float(df.obtained.sum())
    return {"total":obtained,"maximum":maximum,"percent":100*obtained/maximum if maximum else 0,
            "gpa":min(5.0,float(details.GP.mean())),
            "status":"Fail" if (details.Status=="Fail").any() else "Pass"}, details

def load_students():
    with db() as c: return pd.read_sql_query("SELECT * FROM students ORDER BY name",c)

def load_marks():
    with db() as c:
        return pd.read_sql_query("""SELECT m.*,s.name,s.roll,s.institution,s.level,s.class_name
        FROM marks m JOIN students s ON s.id=m.student_id""",c)

if "user" not in st.session_state: st.session_state.user=None
if "dark" not in st.session_state: st.session_state.dark=False

with st.sidebar:
    st.title("🎓 EduNexus")
    st.caption("Version 3.0 • Fresh Build")
    st.session_state.dark=st.toggle("Dark mode",st.session_state.dark)
    if st.session_state.user:
        st.write(f"**{st.session_state.user['username']}**")
        st.write(st.session_state.user["role"])
        if st.button("Logout"):
            st.session_state.user=None
            st.rerun()

if st.session_state.dark:
    st.markdown("<style>.stApp{background:#0b1220;color:#e5e7eb}[data-testid=stSidebar]{background:#111827}</style>",unsafe_allow_html=True)

with db() as c: user_count=c.execute("SELECT COUNT(*) FROM users").fetchone()[0]

if user_count==0:
    st.title("EduNexus 3.0")
    st.subheader("Create first Admin account")
    with st.form("first_admin"):
        u=st.text_input("Admin username")
        p=st.text_input("Password (minimum 8 characters)",type="password")
        p2=st.text_input("Confirm password",type="password")
        go=st.form_submit_button("Create Admin")
    if go:
        if not u.strip() or len(p)<8: st.error("Username দিন এবং অন্তত ৮ অক্ষরের password দিন।")
        elif p!=p2: st.error("Password মিলছে না।")
        else:
            try:
                with db() as c: add_user(c,u,p,"Admin")
                st.success("Admin তৈরি হয়েছে। পেজ refresh করে login করুন।")
                st.rerun()
            except sqlite3.IntegrityError: st.error("Username আগে থেকেই আছে।")
    st.stop()

if st.session_state.user is None:
    st.title("🎓 EduNexus 3.0")
    st.subheader("Academic Result & Analytics Platform")
    with st.form("login"):
        u=st.text_input("Username")
        p=st.text_input("Password",type="password")
        go=st.form_submit_button("Login",use_container_width=True)
    if go:
        user=verify(u,p)
        if user: st.session_state.user=user; st.rerun()
        else: st.error("Username অথবা password ভুল।")
    st.stop()

user=st.session_state.user
students=load_students()
marks=load_marks()
st.title("EduNexus 3.0")
st.caption("School • College • University")

if user["role"]=="Student":
    with db() as c: student=c.execute("SELECT * FROM students WHERE username=?",(user["username"],)).fetchone()
    if not student: st.warning("Student profile Admin-এর সঙ্গে link করা নেই।")
    else:
        st.subheader(student["name"])
        with db() as c:
            exams=[r[0] for r in c.execute("SELECT DISTINCT exam FROM marks WHERE student_id=?",(student["id"],))]
        if exams:
            exam=st.selectbox("Select exam",exams)
            df=pd.read_sql_query("SELECT exam,subject,obtained,total FROM marks WHERE student_id=? AND exam=?",
                                 db(),params=(student["id"],exam))
            summary,details=analyze(df)
            a,b,c,d=st.columns(4)
            a.metric("Total",f"{summary['total']:g}/{summary['maximum']:g}")
            b.metric("Percentage",f"{summary['percent']:.1f}%")
            c.metric("GPA (demo)",f"{summary['gpa']:.2f}/5")
            d.metric("Status",summary["status"])
            st.dataframe(details,use_container_width=True,hide_index=True)
        else: st.info("কোনো result পাওয়া যায়নি।")
else:
    a,b,c,d=st.columns(4)
    a.metric("Students",len(students)); b.metric("Mark entries",len(marks))
    c.metric("Exams",marks.exam.nunique() if not marks.empty else 0)
    d.metric("Subjects",marks.subject.nunique() if not marks.empty else 0)
    tabs=["Dashboard","Students","Marks Entry","AI Insights"]
    if user["role"]=="Admin": tabs+=["User Management","Export"]
    pages=st.tabs(tabs)

    with pages[0]:
        if marks.empty: st.info("প্রথমে student ও marks যোগ করুন।")
        else:
            chart=marks.assign(percent=marks.obtained/marks.total*100)
            st.subheader("Average performance by subject")
            st.bar_chart(chart.groupby("subject").percent.mean())
            st.dataframe(marks[["name","roll","exam","subject","obtained","total"]].tail(12),
                         use_container_width=True,hide_index=True)

    with pages[1]:
        if user["role"]=="Admin":
            with st.expander("Add student"):
                with st.form("student_add"):
                    name=st.text_input("Full name"); roll=st.text_input("Roll")
                    inst=st.text_input("Institution"); level=st.selectbox("Level",["School","College","University"])
                    cls=st.text_input("Class / Year / Semester")
                    year=st.text_input("Academic year",str(datetime.now().year))
                    su=st.text_input("Student username"); sp=st.text_input("Temporary password (8+ chars)",type="password")
                    save=st.form_submit_button("Save student")
                if save:
                    if not all([name.strip(),roll.strip(),inst.strip(),year.strip(),su.strip()]) or len(sp)<8:
                        st.error("সব প্রয়োজনীয় তথ্য দিন; password কমপক্ষে ৮ অক্ষর।")
                    else:
                        try:
                            with db() as c:
                                c.execute("BEGIN")
                                c.execute("""INSERT INTO students(name,roll,institution,level,class_name,academic_year,username)
                                VALUES(?,?,?,?,?,?,?)""",(name.strip(),roll.strip(),inst.strip(),level,cls,year,su.strip()))
                                add_user(c,su,sp,"Student")
                            st.success("Student account তৈরি হয়েছে।"); st.rerun()
                        except sqlite3.IntegrityError: st.error("Roll অথবা username duplicate।")
        q=st.text_input("Search student")
        view=students.copy()
        if q and not view.empty:
            mask=False
            for col in ["name","roll","institution","class_name"]:
                mask=mask|view[col].astype(str).str.contains(q,case=False,na=False)
            view=view[mask]
        st.dataframe(view,use_container_width=True,hide_index=True)

    with pages[2]:
        if students.empty: st.info("আগে student যোগ করুন।")
        else:
            opts={f"{r.name} | Roll {r.roll}":int(r.id) for r in students.itertuples()}
            with st.form("mark_entry"):
                chosen=st.selectbox("Student",list(opts.keys()))
                exam=st.text_input("Exam name"); subject=st.text_input("Subject")
                x,y=st.columns(2)
                obtained=x.number_input("Obtained marks",min_value=0.0,value=0.0)
                total=y.number_input("Total marks",min_value=1.0,value=100.0)
                save=st.form_submit_button("Save / Update marks")
            if save:
                if not exam.strip() or not subject.strip(): st.error("Exam ও subject লিখুন।")
                elif obtained>total: st.error("Obtained marks total-এর বেশি হতে পারবে না।")
                else:
                    with db() as c:
                        c.execute("""INSERT INTO marks(student_id,exam,subject,obtained,total,entered_by,created_at)
                        VALUES(?,?,?,?,?,?,?) ON CONFLICT(student_id,exam,subject) DO UPDATE SET
                        obtained=excluded.obtained,total=excluded.total,entered_by=excluded.entered_by,created_at=excluded.created_at""",
                        (opts[chosen],exam.strip(),subject.strip(),obtained,total,user["username"],datetime.now().isoformat()))
                    st.success("Marks saved."); st.rerun()

    with pages[3]:
        st.subheader("AI Insights — Free explainable analysis")
        st.caption("এটি rule-based analysis; এখনো Machine Learning prediction নয়।")
        if marks.empty: st.info("Insights-এর জন্য আগে result যোগ করুন।")
        else:
            exam=st.selectbox("Choose exam",sorted(marks.exam.unique()),key="insight_exam")
            part=marks[marks.exam==exam].copy()
            part["percent"]=part.obtained/part.total*100
            avg=part.groupby("subject").percent.mean().sort_values()
            if len(avg):
                st.write(f"**সহায়তা প্রয়োজন হতে পারে:** {avg.index[0]} (গড় {avg.iloc[0]:.1f}%)")
                st.write(f"**তুলনামূলক ভালো বিষয়:** {avg.index[-1]} (গড় {avg.iloc[-1]:.1f}%)")
                weak=avg[avg<40]
                st.write("**৪০%-এর নিচে গড়:** "+(", ".join(weak.index) if len(weak) else "কোনো বিষয় নেই"))

    if user["role"]=="Admin":
        with pages[4]:
            with st.form("teacher_add"):
                tu=st.text_input("Teacher username"); tp=st.text_input("Temporary password (8+ chars)",type="password")
                create=st.form_submit_button("Create Teacher")
            if create:
                if not tu.strip() or len(tp)<8: st.error("Username এবং ৮+ অক্ষরের password দিন।")
                else:
                    try:
                        with db() as c: add_user(c,tu,tp,"Teacher")
                        st.success("Teacher তৈরি হয়েছে।"); st.rerun()
                    except sqlite3.IntegrityError: st.error("Username already exists.")
            with db() as c: users=pd.read_sql_query("SELECT username,role,created_at FROM users",c)
            st.dataframe(users,use_container_width=True,hide_index=True)
        with pages[5]:
            if marks.empty: st.info("Export করার মতো data নেই।")
            else:
                st.download_button("Download results CSV",marks.to_csv(index=False).encode("utf-8-sig"),
                                   file_name="edunexus_v3_results.csv",mime="text/csv")

st.divider()
st.caption("Prototype only. Demo grading scale; confirm official rules. Use fictional student data until security and persistent storage are configured.")
