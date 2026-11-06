import os, mysql.connector
from dotenv import load_dotenv
load_dotenv()
cfg=dict(host=os.getenv("DB_HOST","localhost"),user=os.getenv("DB_USER","root"),
         password=os.getenv("DB_PASSWORD",""),port=int(os.getenv("DB_PORT","3306")))
conn=mysql.connector.connect(**cfg)
cur=conn.cursor()
with open("schema.sql",encoding="utf-8") as f:
    statements=[s.strip() for s in f.read().split(";") if s.strip()]
for statement in statements:
    cur.execute(statement)
conn.commit()
cur.execute("USE "+os.getenv("DB_NAME","student_feedback_db"))
# Ensure the institution used by this project exists without deleting or replacing existing records.
cur.execute("SELECT id FROM colleges WHERE name=%s LIMIT 1", ("Mohan Babu University",))
row=cur.fetchone()
if row:
    college=row[0]
else:
    cur.execute("INSERT INTO colleges(name) VALUES(%s)", ("Mohan Babu University",))
    college=cur.lastrowid

cur.execute("SELECT id FROM campuses WHERE college_id=%s AND name=%s LIMIT 1", (college, "Main Campus"))
campus_row=cur.fetchone()
if not campus_row:
    cur.execute("INSERT INTO campuses(college_id,name) VALUES(%s,%s)", (college, "Main Campus"))

conn.commit()
cur.close(); conn.close()
print("Database initialized. Institution available: Mohan Babu University / Main Campus.")
print("Add faculty accounts, courses and roster entries using MySQL Workbench or the SQL guide.")
