"""MODULE 2 - Neo4j graph: Candidate-[HAS_SKILL]->Skill<-[REQUIRES]-Job, Candidate-[APPLIED_FOR]->Job,
Skill-[CO_OCCURS]-Skill.  Runs on a real Neo4j server; otherwise writes .cypher scripts and runs
the same analysis in Python so the demo still works."""
import json, itertools
from collections import Counter
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

QUERIES = {
 "Top candidates for a job (graph skill match)": """
MATCH (j:Job {job_id:$job})-[:REQUIRES]->(s:Skill)
WITH j, count(s) AS total
MATCH (c:Candidate)-[:APPLIED_FOR]->(j)
OPTIONAL MATCH (c)-[:HAS_SKILL]->(s2:Skill)<-[:REQUIRES]-(j)
WITH c, total, count(s2) AS matched
RETURN c.candidate_id AS id, c.name AS name, matched, total, round(100.0*matched/total) AS match_pct
ORDER BY matched DESC, c.experience DESC LIMIT 5""",
 "Skill gap of a candidate for a job": """
MATCH (c:Candidate {candidate_id:$cand}), (j:Job {job_id:$job})-[:REQUIRES]->(s:Skill)
WHERE NOT (c)-[:HAS_SKILL]->(s)
RETURN c.name AS name, collect(s.name) AS missing_skills""",
 "Skills most often paired with Neo4j (recommendation)": """
MATCH (:Skill {name:'Neo4j'})-[r:CO_OCCURS]-(o:Skill)
RETURN o.name AS skill, r.weight AS together ORDER BY together DESC LIMIT 5""",
 "Most in-demand skills across candidates": """
MATCH (:Candidate)-[:HAS_SKILL]->(s:Skill)
RETURN s.name AS skill, count(*) AS candidates ORDER BY candidates DESC LIMIT 5""",
}

def build_cypher(resumes, jobs):
    L = ["CREATE CONSTRAINT IF NOT EXISTS FOR (c:Candidate) REQUIRE c.candidate_id IS UNIQUE;",
         "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE;",
         "CREATE CONSTRAINT IF NOT EXISTS FOR (j:Job) REQUIRE j.job_id IS UNIQUE;"]
    for j in jobs:
        L.append(f"MERGE (j:Job {{job_id:'{j['job_id']}'}}) SET j.title='{j['title']}', j.department='{j['department']}';")
        for s in j["required_skills"]:
            L.append(f"MATCH (j:Job {{job_id:'{j['job_id']}'}}) MERGE (s:Skill {{name:'{s}'}}) MERGE (j)-[:REQUIRES]->(s);")
    for r in resumes:
        L.append(f"MERGE (c:Candidate {{candidate_id:'{r['candidate_id']}'}}) SET c.name='{r['name']}', "
                 f"c.experience={r['experience_years']}, c.cgpa={r['education']['cgpa']}, c.status='{r['status']}';")
        L.append(f"MATCH (c:Candidate {{candidate_id:'{r['candidate_id']}'}}), (j:Job {{job_id:'{r['applied_job_id']}'}}) MERGE (c)-[:APPLIED_FOR]->(j);")
        for s in r["skills"]:
            L.append(f"MATCH (c:Candidate {{candidate_id:'{r['candidate_id']}'}}) MERGE (s:Skill {{name:'{s}'}}) MERGE (c)-[:HAS_SKILL]->(s);")
    for (a, b), w in cooccurrence(resumes).items():
        if w >= 3:
            L.append(f"MATCH (a:Skill {{name:'{a}'}}), (b:Skill {{name:'{b}'}}) MERGE (a)-[:CO_OCCURS {{weight:{w}}}]->(b);")
    return "\n".join(L)

def cooccurrence(resumes):
    c = Counter()
    for r in resumes:
        for a, b in itertools.combinations(sorted(r["skills"]), 2):
            c[(a, b)] += 1
    return c

def run_on_neo4j(resumes, jobs):
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print(f"[Neo4j] Connected to {NEO4J_URI}")
    with driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")
        for stmt in build_cypher(resumes, jobs).split(";\n"):
            if stmt.strip():
                s.run(stmt.strip().rstrip(";"))
        n = s.run("MATCH (n) RETURN count(n) AS n").single()["n"]
        print(f"[Neo4j] Graph built with {n} nodes")
        params = {"job": "J004", "cand": resumes[0]["candidate_id"]}
        for title, q in QUERIES.items():
            print(f"\n>> {title}")
            for rec in s.run(q, **params):
                print("  ", dict(rec))
    driver.close()

def run_in_python(resumes, jobs):
    """Same four queries computed in Python (fallback when Neo4j is not installed)."""
    print("[Neo4j] Server not reachable -> running equivalent graph analysis in Python.")
    job = next(j for j in jobs if j["job_id"] == "J004"); req = set(job["required_skills"])
    print("\n>> Top candidates for a job (graph skill match)  [job J004]")
    ap = [r for r in resumes if r["applied_job_id"] == "J004"]
    for r in sorted(ap, key=lambda r: (-len(req & set(r["skills"])), -r["experience_years"]))[:5]:
        m = len(req & set(r["skills"])); print(f"   {r['candidate_id']} {r['name']:<20} matched {m}/{len(req)} = {round(100*m/len(req))}%")
    c = resumes[0]
    print(f"\n>> Skill gap of {c['name']} for J004\n   missing:", sorted(req - set(c["skills"])))
    co = Counter()
    for (a, b), w in cooccurrence(resumes).items():
        if a == "Neo4j": co[b] += w
        if b == "Neo4j": co[a] += w
    print("\n>> Skills most often paired with Neo4j\n  ", co.most_common(5))
    print("\n>> Most in-demand skills\n  ", Counter(s for r in resumes for s in r["skills"]).most_common(5))

def run():
    resumes = json.load(open("data/resumes.json")); jobs = json.load(open("data/jobs.json"))
    open("data/load_graph.cypher", "w").write(build_cypher(resumes, jobs))
    open("data/analysis_queries.cypher", "w").write("\n\n".join(f"// {t}\n{q};" for t, q in QUERIES.items()))
    print("Wrote data/load_graph.cypher and data/analysis_queries.cypher (paste into Neo4j Browser if needed)")
    try:
        run_on_neo4j(resumes, jobs)
    except Exception as e:
        run_in_python(resumes, jobs)

if __name__ == "__main__":
    run()
