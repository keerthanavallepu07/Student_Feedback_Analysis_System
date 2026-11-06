# Admin and initial data setup

The database supports multiple colleges and campuses. The setup script creates or reuses `Mohan Babu University` and its `Main Campus`; it does not invent courses, faculty or student records.

## Admin login

Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env`. There is no public admin signup. Sign in through `/admin-login`.

## Add a course (MySQL Workbench)

After running `python setup_db.py`, find the institution and campus IDs:

```sql
USE student_feedback_db;
SELECT c.id AS college_id, c.name AS college, cp.id AS campus_id, cp.name AS campus
FROM colleges c JOIN campuses cp ON cp.college_id = c.id
WHERE c.name = 'Mohan Babu University' AND cp.name = 'Main Campus';
```

Use the returned IDs to add the actual courses offered by your department (replace the sample values):

```sql
INSERT INTO courses (name, college_id, campus_id, department)
VALUES ('Your Course Name', 1, 1, 'Your Department');
```

Do not assume the example IDs are correct; use the IDs returned by the SELECT query. Then open Admin → Manage to create faculty accounts and assign each course to a faculty member. The application checks that the faculty member and course belong to the same college and campus.

## Student roster

Add approved enrollment records from Admin → Manage using the student roster CSV template, or insert them through MySQL Workbench:

```sql
INSERT INTO student_roster (roll_no, college_id, campus_id, branch, year_level, section)
VALUES ('YOUR_ROLL_NO', 1, 1, 'CSE', 1, 'A');
```

Replace the IDs and student details with valid values. Student signup checks roll number, college, campus, branch, year and section against an active roster row.

## Rating scale and feedback prompts

1 Poor · 2 Below Average · 3 Average · 4 Good · 5 Excellent

The current form stores one overall course rating and an optional comment. Per-question ratings are a possible future extension.
