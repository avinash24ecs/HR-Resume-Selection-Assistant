"""MODULE 3 - Data warehouse: ETL from MongoDB -> star schema (SQLite) + OLAP queries."""
import os, sqlite3
from datetime import date
from config import WAREHOUSE_DB
from db import get_db

DDL = """
DROP TABLE IF EXISTS fact_application; DROP TABLE IF EXISTS fact_candidate_skill;
DROP TABLE IF EXISTS dim_candidate; DROP TABLE IF EXISTS dim_job; DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_education; DROP TABLE IF EXISTS dim_skill;
CREATE TABLE dim_candidate(candidate_key INTEGER PRIMARY KEY, candidate_id TEXT, name TEXT, city TEXT, exp_band TEXT);
CREATE TABLE dim_job(job_key INTEGER PRIMARY KEY, job_id TEXT, title TEXT, department TEXT, location TEXT);
CREATE TABLE dim_date(date_key INTEGER PRIMARY KEY, full_date TEXT, day INT, month INT, month_name TEXT, quarter INT, year INT);
CREATE TABLE dim_education(edu_key INTEGER PRIMARY KEY, degree TEXT, field TEXT);
CREATE TABLE dim_skill(skill_key INTEGER PRIMARY KEY, skill_name TEXT);
CREATE TABLE fact_application(app_key INTEGER PRIMARY KEY, candidate_key INT, job_key INT, date_key INT, edu_key INT,
  experience_years REAL, cgpa REAL, expected_salary_lpa REAL, skill_count INT, num_certs INT, status TEXT,
  is_shortlisted INT, is_hired INT);
CREATE TABLE fact_candidate_skill(candidate_key INT, skill_key INT);
"""

def exp_band(e):
    return "Fresher (<1)" if e < 1 else "Junior (1-3)" if e < 3 else "Mid (3-5)" if e < 5 else "Senior (5+)"

def etl(db=None, path=WAREHOUSE_DB, verbose=True):
    """EXTRACT from MongoDB -> TRANSFORM (clean, derive bands, surrogate keys) -> LOAD into star schema."""
    db = db or get_db()
    if db.resumes.count_documents({}) == 0:
        import mongo_ops; mongo_ops.load_json_to_mongo(db)
    resumes = list(db.resumes.find({}, {"_id": 0})); jobs = list(db.jobs.find({}, {"_id": 0}))
    if path != ":memory:":
        os.makedirs(os.path.dirname(path), exist_ok=True)
    con = sqlite3.connect(path, check_same_thread=False); con.executescript(DDL)
    jkey = {j["job_id"]: i for i, j in enumerate(jobs, 1)}
    con.executemany("INSERT INTO dim_job VALUES(?,?,?,?,?)",
                    [(jkey[j["job_id"]], j["job_id"], j["title"], j["department"], j["location"]) for j in jobs])
    edu, skl = {}, {}
    for n, r in enumerate(resumes, 1):
        e = (r["education"]["degree"], r["education"]["field"]); edu.setdefault(e, len(edu) + 1)
        for s in r["skills"]: skl.setdefault(s, len(skl) + 1)
        d = date.fromisoformat(r["applied_on"]); dk = int(d.strftime("%Y%m%d"))
        con.execute("INSERT OR IGNORE INTO dim_date VALUES(?,?,?,?,?,?,?)",
                    (dk, str(d), d.day, d.month, d.strftime("%b"), (d.month - 1) // 3 + 1, d.year))
        con.execute("INSERT INTO dim_candidate VALUES(?,?,?,?,?)",
                    (n, r["candidate_id"], r["name"], r["city"], exp_band(r["experience_years"])))
        con.execute("INSERT INTO fact_application VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (n, n, jkey[r["applied_job_id"]], dk, edu[e], r["experience_years"], r["education"]["cgpa"],
                     r["expected_salary_lpa"], len(r["skills"]), len(r["certifications"]), r["status"],
                     int(r["status"] in ("Shortlisted", "Hired")), int(r["status"] == "Hired")))
        con.executemany("INSERT INTO fact_candidate_skill VALUES(?,?)", [(n, skl[s]) for s in r["skills"]])
    con.executemany("INSERT INTO dim_education VALUES(?,?,?)", [(k, d, f) for (d, f), k in edu.items()])
    con.executemany("INSERT INTO dim_skill VALUES(?,?)", [(k, s) for s, k in skl.items()])
    con.commit()
    cnt = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
           for t in ["dim_candidate", "dim_job", "dim_date", "dim_education", "dim_skill", "fact_application", "fact_candidate_skill"]}
    if verbose: print("[ETL] Star schema loaded:", cnt)
    return con

OLAP = {
 "ROLL-UP: applications & hire rate by department": """
   SELECT j.department, COUNT(*) apps, SUM(is_hired) hired, ROUND(100.0*SUM(is_hired)/COUNT(*),1) hire_pct
   FROM fact_application f JOIN dim_job j USING(job_key) GROUP BY j.department ORDER BY apps DESC""",
 "DRILL-DOWN: department -> job title": """
   SELECT j.department, j.title, COUNT(*) apps, ROUND(AVG(cgpa),2) avg_cgpa, ROUND(AVG(expected_salary_lpa),1) avg_salary
   FROM fact_application f JOIN dim_job j USING(job_key) GROUP BY j.department, j.title ORDER BY 1,3 DESC""",
 "SLICE: 2025 Q1-Q2 shortlisted/hired by month": """
   SELECT d.month, d.month_name, COUNT(*) apps, SUM(is_shortlisted) shortlisted
   FROM fact_application f JOIN dim_date d USING(date_key) WHERE d.quarter IN (1,2) GROUP BY d.month, d.month_name ORDER BY d.month""",
 "DICE: experience band x job (hired count)": """
   SELECT c.exp_band, j.title, SUM(is_hired) hired
   FROM fact_application f JOIN dim_candidate c USING(candidate_key) JOIN dim_job j USING(job_key)
   WHERE j.department IN ('Engineering','Analytics') GROUP BY c.exp_band, j.title ORDER BY c.exp_band, hired DESC""",
 "TOP skills among HIRED candidates": """
   SELECT s.skill_name, COUNT(*) hired_with_skill
   FROM fact_candidate_skill cs JOIN dim_skill s USING(skill_key) JOIN fact_application f ON f.candidate_key=cs.candidate_key
   WHERE f.is_hired=1 GROUP BY s.skill_name ORDER BY 2 DESC LIMIT 6""",
 "Quarterly trend": """
   SELECT d.year, d.quarter, COUNT(*) apps, ROUND(AVG(expected_salary_lpa),2) avg_salary
   FROM fact_application f JOIN dim_date d USING(date_key) GROUP BY d.year, d.quarter ORDER BY 1,2""",
}

def olap_results(con):
    """Run every OLAP query and return {title: {columns, rows}} (used by the web API)."""
    out = {}
    for title, q in OLAP.items():
        cur = con.execute(q)
        out[title] = {"columns": [c[0] for c in cur.description], "rows": [list(r) for r in cur.fetchall()]}
    return out

def run():
    import pandas as pd
    con = etl()
    for title, q in OLAP.items():
        print(f"\n>> {title}")
        print(pd.read_sql_query(q, con).to_string(index=False))
    print("\n>> CUBE-style pivot: Department x Status")
    df = pd.read_sql_query("SELECT j.department, f.status FROM fact_application f JOIN dim_job j USING(job_key)", con)
    print(pd.crosstab(df.department, df.status, margins=True))
    con.close()

if __name__ == "__main__":
    run()
