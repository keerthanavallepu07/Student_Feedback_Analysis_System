import os, csv, io, hmac
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
import mysql.connector
from mysql.connector import pooling

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-development-secret")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

DB_CONFIG = dict(host=os.getenv("DB_HOST","localhost"), user=os.getenv("DB_USER","root"),
                 password=os.getenv("DB_PASSWORD",""), database=os.getenv("DB_NAME","student_feedback_db"),
                 port=int(os.getenv("DB_PORT","3306")))
pool = None

def get_conn():
    global pool
    if pool is None:
        pool = pooling.MySQLConnectionPool(pool_name="feedback_pool", pool_size=5, **DB_CONFIG)
    return pool.get_connection()

def query(sql, params=(), one=False, commit=False):
    conn=get_conn()
    try:
        cur=conn.cursor(dictionary=True)
        cur.execute(sql, params)
        result=cur.fetchone() if one else cur.fetchall()
        if commit: conn.commit()
        return result
    finally:
        try: cur.close()
        except: pass
        conn.close()

def execute(sql, params=()):
    conn=get_conn()
    try:
        cur=conn.cursor()
        cur.execute(sql, params); conn.commit()
        return cur.lastrowid
    finally:
        cur.close(); conn.close()

def sentiment(text, rating):
    t=(text or "").lower()
    negatives=("not good","not clear","hardly clear","unclear","poor","confusing","bad","difficult","unfair","waste","disappoint")
    positives=("excellent","helpful","clear","good","great","effective","well organized","interesting","useful","love")
    if any(x in t for x in negatives): return "Negative"
    if any(x in t for x in positives): return "Positive"
    return "Positive" if rating >= 4 else ("Negative" if rating <= 2 else "Neutral")

def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapped(*a,**k):
            if "user_id" not in session:
                return redirect(url_for("home"))
            if role and session.get("role") != role:
                flash("You do not have permission to access that page.","error")
                return redirect(url_for("home"))
            return fn(*a,**k)
        return wrapped
    return deco

@app.context_processor
def inject_year(): return {"year": datetime.now().year}

@app.route("/")
def home():
    try:
        stats=query("""SELECT COUNT(*) total, ROUND(AVG(rating),1) avg_rating,
                    SUM(sentiment='Positive') positive FROM feedback""", one=True)
    except Exception: stats={"total":0,"avg_rating":0,"positive":0}
    return render_template("home.html", stats=stats or {"total":0,"avg_rating":0,"positive":0})

@app.route("/signup", methods=["GET","POST"])
def signup():
    colleges=query("SELECT id,name FROM colleges WHERE active=1 ORDER BY name")
    campuses=query("SELECT id,college_id,name FROM campuses WHERE active=1 ORDER BY name")
    if request.method=="POST":
        d=request.form
        required=["full_name","email","username","department","password","confirm_password","college_id","campus_id","roll_no","branch","year","section"]
        if any(not d.get(k,"").strip() for k in required):
            flash("Please complete all required fields.","error")
        elif d["password"] != d["confirm_password"]:
            flash("Passwords do not match.","error")
        elif len(d["password"]) < 8:
            flash("Password must contain at least 8 characters.","error")
        else:
            try:
                roster=query("""SELECT id FROM student_roster WHERE roll_no=%s AND college_id=%s AND campus_id=%s
                             AND branch=%s AND year_level=%s AND section=%s AND active=1""",
                             (d["roll_no"].strip(),d["college_id"],d["campus_id"],d["branch"],d["year"],d["section"]),one=True)
                if not roster: flash("Student details were not found in the approved college roster. Contact your college administrator.","error")
                else:
                    execute("""INSERT INTO users(full_name,email,username,department,password_hash,role,college_id,campus_id,roll_no,branch,year_level,section)
                             VALUES(%s,%s,%s,%s,%s,'student',%s,%s,%s,%s,%s,%s)""",
                             (d["full_name"],d["email"],d["username"],d["department"],generate_password_hash(d["password"]),
                              d["college_id"],d["campus_id"],d["roll_no"],d["branch"],d["year"],d["section"]))
                    flash("Account created. Please sign in.","success"); return redirect(url_for("student_login"))
            except mysql.connector.IntegrityError: flash("Email, username, or roll number is already registered.","error")
            except Exception: flash("Could not create account. Check database setup and roster details.","error")
    return render_template("signup.html",colleges=colleges,campuses=campuses)

@app.route("/student-login",methods=["GET","POST"])
def student_login():
    if request.method=="POST":
        u=query("SELECT * FROM users WHERE username=%s AND role='student'",(request.form.get("username",""),),one=True)
        if u and check_password_hash(u["password_hash"],request.form.get("password","")):
            session.clear(); session["user_id"]=u["id"]; session["role"]="student"; session["name"]=u["full_name"]
            session["college_id"]=u["college_id"]; session["campus_id"]=u["campus_id"]
            return redirect(url_for("student_portal"))
        flash("Invalid student username or password.","error")
    return render_template("login.html",kind="Student",endpoint="student_login")

@app.route("/faculty-login",methods=["GET","POST"])
def faculty_login():
    if request.method=="POST":
        u=query("SELECT * FROM users WHERE username=%s AND role='faculty'",(request.form.get("username",""),),one=True)
        if u and check_password_hash(u["password_hash"],request.form.get("password","")):
            session.clear(); session["user_id"]=u["id"]; session["role"]="faculty"; session["name"]=u["full_name"]
            session["college_id"]=u["college_id"]; session["campus_id"]=u["campus_id"]
            return redirect(url_for("faculty_dashboard"))
        flash("Invalid faculty username or password.","error")
    return render_template("login.html",kind="Faculty",endpoint="faculty_login")

@app.route("/admin-login",methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        username=os.getenv("ADMIN_USERNAME","admin")
        password=os.getenv("ADMIN_PASSWORD","")
        if hmac.compare_digest(request.form.get("username",""),username) and password and hmac.compare_digest(request.form.get("password",""),password):
            session.clear(); session["user_id"]=0; session["role"]="admin"; session["name"]="Administrator"
            return redirect(url_for("dashboard"))
        flash("Invalid administrator credentials.","error")
    return render_template("login.html",kind="Administrator",endpoint="admin_login")

@app.route("/student")
@login_required("student")
def student_portal():
    courses=query("""SELECT id,name FROM courses WHERE active=1 AND college_id=%s AND campus_id=%s ORDER BY name""",
                  (session["college_id"],session["campus_id"]))
    history=query("SELECT subject,rating,sentiment,created_at FROM feedback WHERE user_id=%s ORDER BY created_at DESC LIMIT 5",(session["user_id"],))
    return render_template("student_portal.html",courses=courses,history=history)

@app.route("/feedback",methods=["GET","POST"])
@login_required("student")
def feedback():
    courses=query("""SELECT id,name FROM courses WHERE active=1 AND college_id=%s AND campus_id=%s ORDER BY name""",
                  (session["college_id"],session["campus_id"]))
    if request.method=="POST":
        d=request.form
        try: rating=int(d.get("rating","0"))
        except: rating=0
        course=query("SELECT id,name,faculty_id FROM courses WHERE id=%s AND college_id=%s AND campus_id=%s AND active=1",
                     (d.get("course_id"),session["college_id"],session["campus_id"]),one=True)
        if not course or rating not in range(1,6): flash("Choose a valid course and rating.","error")
        else:
            comments=d.get("comments","").strip()
            sent=sentiment(comments,rating)
            execute("""INSERT INTO feedback(user_id,student_name,department,subject,course_id,faculty_id,college_id,campus_id,
                       feedback_question,rating,comments,sentiment,branch,year_level,section)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (session["user_id"],None,"",course["name"],course["id"],course["faculty_id"],
                     session["college_id"],session["campus_id"],"Overall course evaluation",rating,comments,sent,
                     None,None,None))
            session["last_course"]=course["name"]; session["last_sentiment"]=sent
            return redirect(url_for("feedback_success"))
    return render_template("feedback.html",courses=courses)

@app.route("/feedback-success")
@login_required("student")
def feedback_success():
    return render_template("success.html",course=session.pop("last_course","your course"),sentiment=session.pop("last_sentiment","Recorded"))

@app.route("/faculty")
@login_required("faculty")
def faculty_dashboard():
    rows=query("""SELECT subject,COUNT(*) responses,ROUND(AVG(rating),2) avg_rating,
                  SUM(sentiment='Positive') positive,SUM(sentiment='Negative') negative
                  FROM feedback WHERE faculty_id=%s AND college_id=%s AND campus_id=%s
                  GROUP BY course_id,subject ORDER BY subject""",(session["user_id"],session["college_id"],session["campus_id"]))
    return render_template("faculty.html",rows=rows)

@app.route("/dashboard")
@login_required("admin")
def dashboard():
    where=[]; params=[]
    for key,col in [("department","department"),("sentiment","sentiment"),("rating","rating")]:
        val=request.args.get(key,"").strip()
        if val: where.append(f"{col}=%s"); params.append(val)
    search=request.args.get("q","").strip()
    if search: where.append("(subject LIKE %s OR comments LIKE %s)"); params += [f"%{search}%"]*2
    clause=(" WHERE "+" AND ".join(where)) if where else ""
    rows=query("SELECT * FROM feedback"+clause+" ORDER BY created_at DESC LIMIT 500",tuple(params))
    stats=query("""SELECT COUNT(*) total,ROUND(AVG(rating),2) average,
                  SUM(sentiment='Positive') positive,SUM(sentiment='Negative') negative FROM feedback""",one=True)
    ratings=query("SELECT rating,COUNT(*) count FROM feedback GROUP BY rating ORDER BY rating")
    sentiments=query("SELECT sentiment,COUNT(*) count FROM feedback GROUP BY sentiment")
    courses=query("SELECT subject,ROUND(AVG(rating),2) average FROM feedback GROUP BY subject ORDER BY subject")
    depts=query("SELECT department,COUNT(*) count,ROUND(AVG(rating),2) average FROM feedback GROUP BY department ORDER BY department")
    words=query("SELECT comments FROM feedback WHERE comments IS NOT NULL AND comments<>'' ORDER BY created_at DESC LIMIT 300")
    return render_template("dashboard.html",rows=rows,stats=stats or {},ratings=ratings,sentiments=sentiments,courses=courses,depts=depts,
                           keywords=keywords_from([x["comments"] for x in words]),filters=request.args)


@app.route("/admin/manage", methods=["GET", "POST"])
@login_required("admin")
def admin_manage():
    colleges=query("SELECT id,name FROM colleges WHERE active=1 ORDER BY name")
    campuses=query("""SELECT cp.id,cp.name,cp.college_id,c.name college_name
                      FROM campuses cp JOIN colleges c ON c.id=cp.college_id
                      WHERE cp.active=1 ORDER BY c.name,cp.name""")
    faculty=query("""SELECT u.id,u.full_name,u.email,u.username,u.department,u.college_id,u.campus_id,
                     c.name college_name,cp.name campus_name
                     FROM users u LEFT JOIN colleges c ON c.id=u.college_id
                     LEFT JOIN campuses cp ON cp.id=u.campus_id
                     WHERE u.role='faculty' ORDER BY u.full_name""")
    courses_list=query("""SELECT co.id,co.name,co.department,co.faculty_id,u.full_name faculty_name,
                          c.name college_name,cp.name campus_name
                          FROM courses co LEFT JOIN users u ON u.id=co.faculty_id
                          JOIN colleges c ON c.id=co.college_id JOIN campuses cp ON cp.id=co.campus_id
                          WHERE co.active=1 ORDER BY co.name""")
    counts=query("""SELECT (SELECT COUNT(*) FROM users WHERE role='student') students,
       (SELECT COUNT(*) FROM users WHERE role='faculty') faculty,
       (SELECT COUNT(*) FROM student_roster WHERE active=1) roster""",one=True) or {}
    return render_template("admin_manage.html", colleges=colleges,campuses=campuses,
                           faculty=faculty,courses_list=courses_list,counts=counts)

@app.route("/admin/faculty/add", methods=["POST"])
@login_required("admin")
def admin_add_faculty():
    d=request.form
    required=("full_name","email","username","department","password","college_id","campus_id")
    if any(not d.get(k,"").strip() for k in required) or len(d.get("password",""))<8:
        flash("Complete all faculty fields. Password must contain at least 8 characters.","error")
        return redirect(url_for("admin_manage"))
    try:
        valid_campus=query("SELECT id FROM campuses WHERE id=%s AND college_id=%s AND active=1",(d["campus_id"],d["college_id"]),one=True)
        if not valid_campus:
            flash("The selected campus does not belong to that college.","error")
            return redirect(url_for("admin_manage"))
        execute("""INSERT INTO users(full_name,email,username,department,password_hash,role,college_id,campus_id)
                   VALUES(%s,%s,%s,%s,%s,'faculty',%s,%s)""",
                (d["full_name"].strip(),d["email"].strip(),d["username"].strip(),d["department"].strip(),
                 generate_password_hash(d["password"]),d["college_id"],d["campus_id"]))
        flash("Faculty account created successfully.","success")
    except mysql.connector.IntegrityError:
        flash("Email or username is already registered.","error")
    except Exception:
        flash("Could not add faculty. Check college and campus selection.","error")
    return redirect(url_for("admin_manage"))

@app.route("/admin/student/add", methods=["POST"])
@login_required("admin")
def admin_add_student():
    d=request.form
    required=("full_name","email","username","department","password","college_id","campus_id","roll_no","branch","year_level","section")
    if any(not d.get(k,"").strip() for k in required) or len(d.get("password",""))<8:
        flash("Complete all student fields. Password must contain at least 8 characters.","error")
        return redirect(url_for("admin_manage"))
    try:
        valid_campus=query("SELECT id FROM campuses WHERE id=%s AND college_id=%s AND active=1",(d["campus_id"],d["college_id"]),one=True)
        if not valid_campus:
            flash("The selected campus does not belong to that college.","error")
            return redirect(url_for("admin_manage"))
        execute("""INSERT INTO student_roster(roll_no,college_id,campus_id,branch,year_level,section)
                   VALUES(%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE college_id=VALUES(college_id),campus_id=VALUES(campus_id),
                   branch=VALUES(branch),year_level=VALUES(year_level),section=VALUES(section),active=1""",
                (d["roll_no"].strip(),d["college_id"],d["campus_id"],d["branch"].strip(),d["year_level"],d["section"].strip()))
        execute("""INSERT INTO users(full_name,email,username,department,password_hash,role,college_id,campus_id,roll_no,branch,year_level,section)
                   VALUES(%s,%s,%s,%s,%s,'student',%s,%s,%s,%s,%s,%s)""",
                (d["full_name"].strip(),d["email"].strip(),d["username"].strip(),d["department"].strip(),
                 generate_password_hash(d["password"]),d["college_id"],d["campus_id"],d["roll_no"].strip(),
                 d["branch"].strip(),d["year_level"],d["section"].strip()))
        flash("Student account and roster entry created.","success")
    except mysql.connector.IntegrityError:
        flash("Email, username or roll number is already registered. Check existing records.","error")
    except Exception:
        flash("Could not add student. Verify the selected college and campus.","error")
    return redirect(url_for("admin_manage"))

@app.route("/admin/course/assign", methods=["POST"])
@login_required("admin")
def admin_assign_course():
    course_id=request.form.get("course_id","").strip()
    faculty_id=request.form.get("faculty_id","").strip() or None
    try:
        course = query("SELECT id,college_id,campus_id FROM courses WHERE id=%s AND active=1", (course_id,), one=True)
        if not course:
            flash("Select a valid active course.", "error")
            return redirect(url_for("admin_manage"))
        if faculty_id:
            faculty = query("SELECT id FROM users WHERE id=%s AND role='faculty' AND college_id=%s AND campus_id=%s",
                            (faculty_id, course["college_id"], course["campus_id"]), one=True)
            if not faculty:
                flash("The selected faculty member must belong to the same college and campus as the course.", "error")
                return redirect(url_for("admin_manage"))
            execute("UPDATE courses SET faculty_id=%s WHERE id=%s", (faculty_id, course_id))
        else:
            execute("UPDATE courses SET faculty_id=NULL WHERE id=%s", (course_id,))
        flash("Course faculty assignment updated.", "success")
    except Exception:
        flash("Could not update course assignment. Verify the selected course and faculty.", "error")
    return redirect(url_for("admin_manage"))

@app.route("/admin/bulk-upload", methods=["POST"])
@login_required("admin")
def admin_bulk_upload():
    kind=request.form.get("kind","")
    uploaded=request.files.get("file")
    if not uploaded or not uploaded.filename.lower().endswith(".csv"):
        flash("Please choose a CSV file.","error")
        return redirect(url_for("admin_manage"))
    try:
        stream=io.StringIO(uploaded.stream.read().decode("utf-8-sig"),newline="")
        reader=csv.DictReader(stream)
        if kind=="faculty":
            required={"full_name","email","username","department","college_id","campus_id","password"}
        elif kind=="roster":
            required={"roll_no","college_id","campus_id","branch","year_level","section"}
        else:
            flash("Unknown upload type.","error")
            return redirect(url_for("admin_manage"))
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            flash("CSV headers are missing required columns. Check the sample format.","error")
            return redirect(url_for("admin_manage"))
        success=0; skipped=0
        for row in reader:
            try:
                if kind=="faculty":
                    if not all((row.get(k) or "").strip() for k in required) or len(row["password"])<8:
                        skipped+=1; continue
                    campus = query("SELECT id FROM campuses WHERE id=%s AND college_id=%s AND active=1",
                                   (row["campus_id"].strip(), row["college_id"].strip()), one=True)
                    if not campus:
                        skipped+=1; continue
                    execute("""INSERT INTO users(full_name,email,username,department,password_hash,role,college_id,campus_id)
                               VALUES(%s,%s,%s,%s,%s,'faculty',%s,%s)""",
                            (row["full_name"].strip(),row["email"].strip(),row["username"].strip(),
                             row["department"].strip(),generate_password_hash(row["password"]),
                             row["college_id"].strip(),row["campus_id"].strip()))
                else:
                    if not all((row.get(k) or "").strip() for k in required):
                        skipped+=1; continue
                    campus = query("SELECT id FROM campuses WHERE id=%s AND college_id=%s AND active=1",
                                   (row["campus_id"].strip(), row["college_id"].strip()), one=True)
                    if not campus:
                        skipped+=1; continue
                    execute("""INSERT INTO student_roster(roll_no,college_id,campus_id,branch,year_level,section)
                               VALUES(%s,%s,%s,%s,%s,%s)
                               ON DUPLICATE KEY UPDATE college_id=VALUES(college_id),campus_id=VALUES(campus_id),
                               branch=VALUES(branch),year_level=VALUES(year_level),section=VALUES(section),active=1""",
                            (row["roll_no"].strip(),row["college_id"].strip(),row["campus_id"].strip(),
                             row["branch"].strip(),row["year_level"].strip(),row["section"].strip()))
                success+=1
            except mysql.connector.IntegrityError:
                skipped+=1
        flash(f"Upload completed: {success} imported, {skipped} skipped. Roster upload enables verified student self-registration; it does not create student passwords.","success" if success else "error")
    except Exception:
        flash("Could not read CSV. Save it as UTF-8 CSV and verify its headers and values.","error")
    return redirect(url_for("admin_manage"))


def keywords_from(texts):
    import re
    stop=set("the and was is are this that with for have has very course instructor class good bad".split())
    counts={}
    for t in texts:
        for w in re.findall(r"[a-zA-Z]{4,}",(t or "").lower()):
            if w not in stop: counts[w]=counts.get(w,0)+1
    return sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:12]

@app.route("/export-csv")
@login_required("admin")
def export_csv():
    rows=query("SELECT created_at,department,subject,rating,comments,sentiment FROM feedback ORDER BY created_at DESC")
    out=io.StringIO(); w=csv.writer(out); w.writerow(["Date","Department","Course","Rating","Comments","Sentiment"])
    for r in rows: w.writerow([r["created_at"],r["department"],r["subject"],r["rating"],r["comments"],r["sentiment"]])
    resp=make_response(out.getvalue()); resp.headers["Content-Disposition"]="attachment; filename=student_feedback_report.csv"; resp.headers["Content-Type"]="text/csv; charset=utf-8"
    return resp

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

if __name__=="__main__":
    app.run(debug=os.getenv("FLASK_DEBUG","false").lower()=="true")
