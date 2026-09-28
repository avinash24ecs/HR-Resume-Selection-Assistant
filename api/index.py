"""Vercel serverless entry point & local Flask API for HR Resume Selection Assistant.
Local run: python api/index.py
"""
import os, sys, json, itertools, uuid
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from flask import Flask, jsonify, request, send_from_directory
import mongo_ops, warehouse, db as dbmod, resume_parser
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

app = Flask(__name__)
_S = {}

def S():
    """Lazy one-time setup: MongoDB + in-memory star-schema warehouse."""
    if not _S:
        d = dbmod.get_db(verbose=False)
        if d.resumes.count_documents({}) == 0:
            mongo_ops.load_json_to_mongo(d)
        _S["db"] = d
        _S["wh"] = warehouse.etl(d, ":memory:", verbose=False)
    return _S

def err(msg, code=400):
    return jsonify({"error": msg}), code

def csv_arg(name):
    return [x.strip() for x in request.args.get(name, "").split(",") if x.strip()]

def num_arg(name, default, lo, hi):
    try:
        return max(lo, min(hi, float(request.args.get(name, default))))
    except (ValueError, TypeError):
        return default

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    return response

@app.route("/api/<path:subpath>", methods=["OPTIONS"])
def handle_options(subpath):
    return jsonify(status="ok"), 200

from werkzeug.exceptions import HTTPException

@app.errorhandler(Exception)
def crash(e):
    if isinstance(e, HTTPException):
        return err(e.description, e.code)
    return err(f"{type(e).__name__}: {e}", 500)

@app.get("/")
def home():
    return send_from_directory(os.path.join(ROOT, "public"), "index.html")

@app.get("/health")
@app.get("/api/health")
def health():
    s = S()
    return jsonify(
        status="ok",
        mongo=dbmod.SOURCE,
        neo4j="configured" if os.getenv("NEO4J_URI") else "not configured (python fallback)",
        resumes=s["db"].resumes.count_documents({}),
        jobs=s["db"].jobs.count_documents({})
    )

# ---------- Jobs Endpoints ----------
@app.get("/api/jobs")
def get_jobs():
    return jsonify(list(S()["db"].jobs.find({}, {"_id": 0})))

@app.post("/api/jobs")
def create_job():
    payload = request.get_json(force=True, silent=True) or {}
    title = payload.get("title", "").strip()
    if not title:
        return err("Job title is required")
    db = S()["db"]
    job_count = db.jobs.count_documents({})
    job_id = payload.get("job_id") or f"J{job_count+1:03d}"
    job_doc = {
        "job_id": job_id,
        "title": title,
        "department": payload.get("department", "Engineering"),
        "required_skills": payload.get("required_skills", []),
        "min_experience": float(payload.get("min_experience", 1.0)),
        "min_cgpa": float(payload.get("min_cgpa", 6.5)),
        "location": payload.get("location", "Mumbai"),
        "openings": int(payload.get("openings", 1))
    }
    db.jobs.replace_one({"job_id": job_id}, job_doc, upsert=True)
    return jsonify({"success": True, "job": job_doc})

# ---------- Resumes Endpoints ----------
@app.get("/api/resumes")
def get_resumes():
    d = S()["db"]
    q = {}
    job_id = request.args.get("job_id")
    if job_id and job_id.upper() != "ALL":
        q["applied_job_id"] = job_id.upper()
    status = request.args.get("status")
    if status and status.lower() != "all":
        q["status"] = status
    search = request.args.get("search", "").strip()
    if search:
        q["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"candidate_id": {"$regex": search, "$options": "i"}},
            {"skills": {"$regex": search, "$options": "i"}},
            {"city": {"$regex": search, "$options": "i"}}
        ]
    limit = int(num_arg("limit", 200, 1, 500))
    resumes = list(d.resumes.find(q, {"_id": 0}).limit(limit))
    return jsonify({"total": len(resumes), "resumes": resumes})

@app.post("/api/resumes")
def add_resume():
    payload = request.get_json(force=True, silent=True) or {}
    db = S()["db"]
    count = db.resumes.count_documents({})
    cand_id = payload.get("candidate_id") or f"C{count+1:03d}"
    resume_doc = {
        "candidate_id": cand_id,
        "name": payload.get("name", "New Candidate"),
        "email": payload.get("email", f"candidate{count+1}@mail.com"),
        "phone": payload.get("phone", "+91 98765 43210"),
        "city": payload.get("city", "Mumbai"),
        "education": payload.get("education", {"degree": "B.Tech", "field": "Computer Science", "cgpa": 7.5, "year": 2024}),
        "experience_years": float(payload.get("experience_years", 1.0)),
        "skills": payload.get("skills", []),
        "certifications": payload.get("certifications", []),
        "projects": payload.get("projects", []),
        "summary": payload.get("summary", ""),
        "expected_salary_lpa": float(payload.get("expected_salary_lpa", 6.0)),
        "applied_job_id": payload.get("applied_job_id", "J001"),
        "applied_on": payload.get("applied_on", "2026-09-28"),
        "status": payload.get("status", "Applied")
    }
    db.resumes.replace_one({"candidate_id": cand_id}, resume_doc, upsert=True)
    return jsonify({"success": True, "candidate": resume_doc})

@app.patch("/api/resumes/<candidate_id>")
def update_resume_status(candidate_id):
    payload = request.get_json(force=True, silent=True) or {}
    db = S()["db"]
    update_fields = {}
    if "status" in payload:
        update_fields["status"] = payload["status"]
    if "notes" in payload:
        update_fields["notes"] = payload["notes"]
    if not update_fields:
        return err("No fields to update")
    res = db.resumes.update_one({"candidate_id": candidate_id.upper()}, {"$set": update_fields})
    if res.matched_count == 0:
        return err("Candidate not found", 404)
    return jsonify({"success": True, "candidate_id": candidate_id.upper(), "updated": update_fields})

@app.delete("/api/resumes/<candidate_id>")
def delete_resume(candidate_id):
    db = S()["db"]
    res = db.resumes.delete_one({"candidate_id": candidate_id.upper()})
    return jsonify({"success": True, "deleted": res.deleted_count > 0})

# ---------- Smart Parsing & ATS Scoring Endpoints ----------
@app.post("/api/parse_resume")
def parse_resume():
    payload = request.get_json(force=True, silent=True) or {}
    text = payload.get("text", "")
    if not text:
        return err("Resume text is required")
    parsed = resume_parser.parse_resume_text(text)
    return jsonify(parsed)

@app.post("/api/score_resume")
def score_resume():
    payload = request.get_json(force=True, silent=True) or {}
    candidate = payload.get("candidate")
    job = payload.get("job")
    if not candidate or not job:
        return err("Both candidate and job objects are required")
    scored = resume_parser.score_candidate_for_job(candidate, job)
    return jsonify(scored)

# ---------- Existing ADBMS Endpoints ----------
@app.get("/api/rank/<job_id>")
def rank(job_id):
    out = mongo_ops.rank_candidates(S()["db"], job_id.upper(), int(num_arg("top", 10, 1, 50)), verbose=False)
    return err(f"Unknown job {job_id}", 404) if out is None else jsonify(out)

@app.get("/api/search")
def search():
    """MongoDB query: /api/search?skills=Python,SQL&min_exp=2&min_cgpa=7&city=Mumbai"""
    q = {"experience_years": {"$gte": num_arg("min_exp", 0, 0, 40)}, "education.cgpa": {"$gte": num_arg("min_cgpa", 0, 0, 10)}}
    if csv_arg("skills"): q["skills"] = {"$all": csv_arg("skills")}
    if request.args.get("city"): q["city"] = request.args["city"]
    docs = S()["db"].resumes.find(q, {"_id": 0, "candidate_id": 1, "name": 1, "city": 1, "skills": 1, "experience_years": 1, "status": 1}).sort("experience_years", -1).limit(25)
    return jsonify(list(docs))

@app.get("/api/skills/top")
def top_skills():
    pipe = [{"$unwind": "$skills"}, {"$group": {"_id": "$skills", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}, {"$limit": 10}]
    return jsonify([{"skill": r["_id"], "candidates": r["n"]} for r in S()["db"].resumes.aggregate(pipe)])

@app.get("/api/match")
def match():
    """Best-fit jobs for a profile: /api/match?skills=SQL,MongoDB&exp=2&cgpa=8"""
    have, exp, cg = set(csv_arg("skills")), num_arg("exp", 1, 0, 40), num_arg("cgpa", 7.5, 0, 10)
    d = S()["db"]; jobs_ = list(d.jobs.find({}, {"_id": 0})); byid = {j["job_id"]: j for j in jobs_}
    hist = []
    for r in d.resumes.find({}, {"_id": 0, "skills": 1, "applied_job_id": 1, "status": 1}):
        req = byid[r["applied_job_id"]]["required_skills"]
        hist.append((100 * len(set(req) & set(r["skills"])) / len(req), r["status"] != "Rejected"))
    out = []
    for j in jobs_:
        req = j["required_skills"]; pct = 100 * len(have & set(req)) / len(req)
        score = pct * .6 + (20 if exp >= j["min_experience"] else exp / max(j["min_experience"], 1) * 20) + cg * 2
        sim = [ok for p, ok in hist if abs(p - pct) <= 15]
        out.append({
            "job_id": j["job_id"], "title": j["title"], "skill_match_pct": round(pct), "score": round(score, 1),
            "missing": sorted(set(req) - have), "historical_selection_rate_pct": round(100 * sum(sim) / len(sim)) if sim else None,
            "similar_profiles": len(sim)
        })
    return jsonify(sorted(out, key=lambda x: -x["score"]))

@app.get("/api/warehouse")
def wh():
    return jsonify(warehouse.olap_results(S()["wh"]))

@app.get("/api/mining")
def mining_results():
    return jsonify(json.load(open(os.path.join(ROOT, "data", "mining_results.json"))))

# ---------- Neo4j (Aura) with automatic Python fallback ----------
def neo4j_run(query, **params):
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), connection_timeout=5)
    try:
        with drv.session() as s:
            return [dict(r) for r in s.run(query, **params)]
    finally:
        drv.close()

def graph(neo_q, params, fallback):
    if os.getenv("NEO4J_URI"):
        try:
            rows = neo4j_run(neo_q, **params)
            if rows: return jsonify(source="neo4j", results=rows)
        except Exception:
            pass
    return jsonify(source="python-fallback", results=fallback())

@app.get("/api/graph/related")
def g_related():
    skill = request.args.get("skill", "Neo4j")
    def fb():
        c = Counter()
        for r in S()["db"].resumes.find({"skills": skill}, {"skills": 1}):
            c.update(x for x in r["skills"] if x != skill)
        return [{"skill": k, "together": v} for k, v in c.most_common(5)]
    return graph("MATCH (:Skill {name:$skill})-[r:CO_OCCURS]-(o:Skill) RETURN o.name AS skill, r.weight AS together ORDER BY together DESC LIMIT 5", {"skill": skill}, fb)

@app.get("/api/graph/gap")
def g_gap():
    cand, job = request.args.get("candidate", "C001"), request.args.get("job", "J004").upper()
    d = S()["db"]; c = d.resumes.find_one({"candidate_id": cand}); j = d.jobs.find_one({"job_id": job})
    if not c or not j: return err("Unknown candidate or job", 404)
    return graph("MATCH (c:Candidate {candidate_id:$cand}), (j:Job {job_id:$job})-[:REQUIRES]->(s:Skill) WHERE NOT (c)-[:HAS_SKILL]->(s) RETURN c.name AS name, collect(s.name) AS missing_skills",
                 {"cand": cand, "job": job}, lambda: [{"name": c["name"], "missing_skills": sorted(set(j["required_skills"]) - set(c["skills"]))}])

@app.get("/api/graph/match")
def g_match():
    job = request.args.get("job", "J004").upper(); j = S()["db"].jobs.find_one({"job_id": job})
    if not j: return err("Unknown job", 404)
    def fb():
        req = set(j["required_skills"]); rows = []
        for r in S()["db"].resumes.find({"applied_job_id": job}, {"_id": 0}):
            rows.append({"id": r["candidate_id"], "name": r["name"], "matched": len(req & set(r["skills"])), "total": len(req), "exp": r["experience_years"]})
        return sorted(rows, key=lambda x: (-x["matched"], -x["exp"]))[:5]
    return graph("MATCH (j:Job {job_id:$job})-[:REQUIRES]->(s:Skill) WITH j, count(s) AS total MATCH (c:Candidate)-[:APPLIED_FOR]->(j) OPTIONAL MATCH (c)-[:HAS_SKILL]->(s2:Skill)<-[:REQUIRES]-(j) WITH c, total, count(s2) AS matched RETURN c.candidate_id AS id, c.name AS name, matched, total ORDER BY matched DESC, c.experience DESC LIMIT 5",
                 {"job": job}, fb)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Starting HR Resume Selection Assistant on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
