"""Vercel serverless entry point (Flask).  Local run:  python api/index.py"""
import os, sys, json, itertools
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)

from flask import Flask, jsonify, request, send_from_directory
import mongo_ops, warehouse, db as dbmod
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

app = Flask(__name__)
_S = {}

def S():
    """Lazy one-time setup per serverless instance: MongoDB + in-memory star-schema warehouse."""
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
    except ValueError:
        return default

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
    return jsonify(status="ok", mongo=dbmod.SOURCE, neo4j="configured" if os.getenv("NEO4J_URI") else "not configured (python fallback)",
                   resumes=s["db"].resumes.count_documents({}), jobs=s["db"].jobs.count_documents({}))

@app.get("/api/jobs")
def jobs():
    return jsonify(list(S()["db"].jobs.find({}, {"_id": 0})))

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
        out.append({"job_id": j["job_id"], "title": j["title"], "skill_match_pct": round(pct), "score": round(score, 1),
                    "missing": sorted(set(req) - have), "historical_selection_rate_pct": round(100 * sum(sim) / len(sim)) if sim else None,
                    "similar_profiles": len(sim)})
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
    app.run(port=int(os.getenv("PORT", 5000)), debug=False)
