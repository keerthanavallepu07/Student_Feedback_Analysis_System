# Student Feedback Analysis System

A Flask + MySQL academic project starter with student roster validation, separate student/faculty/admin entry points, sentiment tagging, analytics charts and CSV export.

## Requirements
- Windows 10/11
- Python 3.10–3.12 recommended
- MySQL Server 8.x and MySQL Workbench
- Internet connection for Chart.js CDN

## Setup (Windows PowerShell)
1. Extract this ZIP and open the extracted folder in VS Code.
2. Open Terminal → PowerShell and run:

```powershell
py -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

3. Open `.env` and enter your own MySQL password and a strong admin password. Do not share `.env`.
4. Ensure MySQL Server is running. Then initialize the database:

```powershell
python setup_db.py
```

5. Start the website:

```powershell
python app.py
```

6. Open http://127.0.0.1:5000/

## Initial institution and project data
- `python setup_db.py` ensures `Mohan Babu University` and its `Main Campus` exist.
- The setup script does not create fake students, faculty accounts, courses or feedback. Add real project data through the admin management page or the SQL instructions in `docs/ADMIN_SETUP.md`.
- Set the administrator credentials in `.env` (`ADMIN_USERNAME`, `ADMIN_PASSWORD`).
- Create faculty accounts and course records before collecting feedback. Add approved student roster entries before student self-registration.

## Tests
Run:

```powershell
python -m pytest tests/
```

The included tests check sentiment rules and basic project files. Database-backed browser workflows should also be manually checked with your local MySQL setup before a viva/demo.

## Important implementation notes
- Admin is a single environment-configured account; there is no public admin signup.
- Faculty dashboards are restricted to feedback mapped to that faculty's assigned courses.
- Admin dashboard includes KPIs, four Chart.js visualizations, filters, keyword highlights and CSV export.
- Sentiment is an offline rule-based baseline, not a trained NLP model.
- Multi-college and multi-campus schema is supported. The admin management page supports faculty creation, student creation, roster upload and faculty-course assignment. Institution and course creation are performed through MySQL Workbench as described in `docs/ADMIN_SETUP.md`.
- This is an academic starter, not a production-hardened deployment. Set a strong SECRET_KEY, HTTPS, CSRF protection, rate limiting, backups and institutional authorization before public deployment.


## Admin management (added)
After signing in at `/admin-login`, open `/admin/manage` to:
- Add faculty accounts manually or upload a faculty CSV.
- Add an individual student account and matching roster entry.
- Upload a student roster CSV so students can create their own accounts through the existing verified signup flow.
- Assign existing courses to faculty members.

CSV templates are available from the admin management page. Faculty CSV columns:
`full_name,email,username,department,college_id,campus_id,password`

Student roster CSV columns:
`roll_no,college_id,campus_id,branch,year_level,section`

The college and campus IDs are shown in the manual-entry dropdowns. The student roster upload creates approved enrollment records, not student login accounts. This lets each student choose their own password during signup.

## Privacy
Student names are not stored in new feedback submissions. The feedback row retains the internal `user_id` so the student can see their own recent submission history, but faculty pages and admin feedback tables/exports do not display student identities. Faculty dashboards show course-level aggregates only. This protects identity from faculty, not from a database administrator with direct database access.

## Mohan Babu University
Running `python setup_db.py` ensures `Mohan Babu University` and its `Main Campus` exist in the configured database. It does not drop or replace existing tables or records.
