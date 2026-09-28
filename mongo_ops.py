"""MODULE 1 - JSON + MongoDB: load JSON, CRUD, indexes, queries, aggregation, resume ranking."""
import json
from db import get_db

def load_json_to_mongo(db):
    db.resumes.drop(); db.jobs.drop()
    db.resumes.insert_many(json.load(open("data/resumes.json")))
    db.jobs.insert_many(json.load(open("data/jobs.json")))
    print(f"Loaded {db.resumes.count_documents({})} resumes, {db.jobs.count_documents({})} jobs from JSON.")

def create_indexes(db):
    db.resumes.create_index("candidate_id", unique=True)
    db.resumes.create_index([("skills", 1)])                         # multikey index on array
    db.resumes.create_index([("education.cgpa", -1), ("experience_years", -1)])  # compound
    try:
        db.resumes.create_index([("summary", "text")])               # text index (real MongoDB)
    except Exception:
        pass
    print("Indexes:", list(db.resumes.index_information().keys()))

def crud_demo(db):
    print("\n--- CRUD DEMO ---")
    # CREATE
    db.resumes.insert_one({"candidate_id": "C999", "name": "Demo User", "skills": ["Python"],
                           "experience_years": 0.5, "education": {"cgpa": 8.1}, "status": "Applied",
                           "applied_job_id": "J001", "expected_salary_lpa": 4})
    # READ
    print("READ   :", db.resumes.find_one({"candidate_id": "C999"}, {"_id": 0, "name": 1, "skills": 1}))
    # UPDATE ($set, $addToSet, $inc)
    db.resumes.update_one({"candidate_id": "C999"},
        {"$set": {"status": "Shortlisted"}, "$addToSet": {"skills": "SQL"}, "$inc": {"experience_years": 0.5}})
    print("UPDATE :", db.resumes.find_one({"candidate_id": "C999"}, {"_id": 0, "status": 1, "skills": 1, "experience_years": 1}))
    # DELETE
    r = db.resumes.delete_one({"candidate_id": "C999"})
    print("DELETE : removed", r.deleted_count)

def query_demo(db):
    print("\n--- QUERY OPERATIONS ---")
    q1 = {"skills": {"$all": ["Python", "SQL"]}, "experience_years": {"$gte": 2}, "education.cgpa": {"$gte": 7.5}}
    res = list(db.resumes.find(q1, {"_id": 0, "candidate_id": 1, "name": 1, "experience_years": 1}).sort("experience_years", -1).limit(5))
    print("Python AND SQL, exp>=2, CGPA>=7.5 (top 5):"); [print("  ", r) for r in res]

    q2 = {"$or": [{"skills": "Neo4j"}, {"skills": "MongoDB"}], "city": {"$in": ["Mumbai", "Pune"]}}
    print("Neo4j/MongoDB candidates in Mumbai/Pune:", db.resumes.count_documents(q2))

    q3 = {"certifications": {"$exists": True, "$ne": []}, "expected_salary_lpa": {"$lte": 8}}
    print("Certified & expected salary <= 8 LPA:", db.resumes.count_documents(q3))

    # bulk update: flag freshers
    r = db.resumes.update_many({"experience_years": {"$lt": 1}}, {"$set": {"category": "Fresher"}})
    print("Bulk update - tagged freshers:", r.modified_count)

def aggregation_demo(db):
    print("\n--- AGGREGATION PIPELINES ---")
    print("1) Top 8 most common skills ($unwind + $group):")
    for r in db.resumes.aggregate([{"$unwind": "$skills"}, {"$group": {"_id": "$skills", "n": {"$sum": 1}}},
                                   {"$sort": {"n": -1}}, {"$limit": 8}]):
        print(f"   {r['_id']:<20}{r['n']}")

    print("2) Status funnel per job ($group):")
    pipe = [{"$group": {"_id": {"job": "$applied_job_id", "status": "$status"}, "count": {"$sum": 1}}},
            {"$sort": {"_id.job": 1, "_id.status": 1}}]
    for r in db.resumes.aggregate(pipe):
        print(f"   {r['_id']['job']} {r['_id']['status']:<12}{r['count']}")

    print("3) Avg CGPA / experience / salary by degree ($group):")
    for r in db.resumes.aggregate([{"$group": {"_id": "$education.degree", "cgpa": {"$avg": "$education.cgpa"},
             "exp": {"$avg": "$experience_years"}, "sal": {"$avg": "$expected_salary_lpa"}, "n": {"$sum": 1}}},
             {"$sort": {"n": -1}}]):
        print(f"   {r['_id']:<8} n={r['n']:<3} cgpa={r['cgpa']:.2f} exp={r['exp']:.2f} salary={r['sal']:.2f}")

def rank_candidates(db, job_id, top=10, verbose=True):
    """Resume selection: score each applicant against a job using an aggregation pipeline."""
    job = db.jobs.find_one({"job_id": job_id})
    if not job:
        if verbose: print("Unknown job", job_id)
        return None
    req = job["required_skills"]
    pipe = [
      {"$match": {"education.cgpa": {"$gte": job["min_cgpa"] - 1}}},
      {"$addFields": {
          "matched": {"$setIntersection": ["$skills", req]},
      }},
      {"$addFields": {
          "match_pct": {"$multiply": [{"$divide": [{"$size": "$matched"}, len(req)]}, 100]},
          "exp_ok": {"$gte": ["$experience_years", job["min_experience"]]},
      }},
      {"$addFields": {
          "score": {"$add": [
              {"$multiply": ["$match_pct", 0.6]},
              {"$cond": ["$exp_ok", 20, {"$multiply": [{"$divide": ["$experience_years", max(job["min_experience"], 1)]}, 20]}]},
              {"$multiply": ["$education.cgpa", 2]},
          ]}}},
      {"$sort": {"score": -1}}, {"$limit": top},
      {"$project": {"_id": 0, "candidate_id": 1, "name": 1, "matched": 1, "missing_count": {"$subtract": [len(req), {"$size": "$matched"}]},
                    "experience_years": 1, "cgpa": "$education.cgpa", "score": {"$round": ["$score", 1]}}},
    ]
    try:
        out = list(db.resumes.aggregate(pipe))
    except NotImplementedError:
        # mongomock lacks $setIntersection; identical scoring done in Python (real MongoDB uses the pipeline above)
        out = []
        for d in db.resumes.find({"education.cgpa": {"$gte": job["min_cgpa"] - 1}}):
            m = [s for s in d["skills"] if s in req]
            pct = len(m) / len(req) * 100
            e = d["experience_years"]
            sc = pct * 0.6 + (20 if e >= job["min_experience"] else e / max(job["min_experience"], 1) * 20) + d["education"]["cgpa"] * 2
            out.append({"candidate_id": d["candidate_id"], "name": d["name"], "matched": m, "experience_years": e,
                        "cgpa": d["education"]["cgpa"], "score": round(sc, 1)})
        out = sorted(out, key=lambda x: -x["score"])[:top]
    if verbose: print(f"\n=== TOP {top} CANDIDATES FOR {job['title']} ({job_id}) | needs {req} ===")
    for i, r in enumerate(out if verbose else [], 1):
        print(f"{i:>2}. {r['candidate_id']} {r['name']:<20} score={r['score']:<5} exp={r['experience_years']:<4} cgpa={r['cgpa']:<4} matched={r['matched']}")
    return out

def run_all(db):
    load_json_to_mongo(db); create_indexes(db); crud_demo(db); query_demo(db); aggregation_demo(db)
    rank_candidates(db, "J004")

if __name__ == "__main__":
    run_all(get_db())
