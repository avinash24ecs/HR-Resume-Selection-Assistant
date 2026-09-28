"""HR Resume Selection Assistant - entry point.
   python main.py all            run every module
   python main.py rank J002      rank applicants for a job (MongoDB pipeline)
   python main.py match "Python,SQL,Pandas" --exp 2 --cgpa 8    find best jobs/candidates for a skill set
"""
import argparse, os, json

def ensure_data():
    if not os.path.exists("data/resumes.json"):
        import generate_data; generate_data.make()

def main():
    ap = argparse.ArgumentParser(description="HR Resume Selection Assistant")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("all"); sub.add_parser("mongo"); sub.add_parser("graph"); sub.add_parser("dw"); sub.add_parser("mine")
    r = sub.add_parser("rank"); r.add_argument("job_id"); r.add_argument("--top", type=int, default=10)
    m = sub.add_parser("match"); m.add_argument("skills"); m.add_argument("--exp", type=float, default=1); m.add_argument("--cgpa", type=float, default=7.5)
    a = ap.parse_args(); ensure_data()
    if a.cmd in (None, "all"):
        import mongo_ops, neo4j_graph, warehouse, mining
        for name, fn in [("1. MONGODB", lambda: mongo_ops.run_all(mongo_ops.get_db())), ("2. NEO4J GRAPH", neo4j_graph.run),
                         ("3. DATA WAREHOUSE", warehouse.run), ("4. DATA MINING", mining.run)]:
            print("\n" + "=" * 70 + f"\n  {name}\n" + "=" * 70); fn()
    elif a.cmd == "mongo": import mongo_ops; mongo_ops.run_all(mongo_ops.get_db())
    elif a.cmd == "graph": import neo4j_graph; neo4j_graph.run()
    elif a.cmd == "dw": import warehouse; warehouse.run()
    elif a.cmd == "mine": import mining; mining.run()
    elif a.cmd == "rank":
        import mongo_ops; db = mongo_ops.get_db(); mongo_ops.load_json_to_mongo(db); mongo_ops.rank_candidates(db, a.job_id, a.top)
    elif a.cmd == "match":
        import mining
        resumes, jobs = mining.load(); df = mining.features(resumes, jobs); clf, cols = mining.classification(df)
        skills = [s.strip() for s in a.skills.split(",")]
        print("\n=== BEST-FIT JOBS FOR THIS PROFILE ===")
        for j in sorted(jobs, key=lambda j: -mining.predict_new(clf, cols, j, skills, a.exp, a.cgpa)[1]):
            p, mt = mining.predict_new(clf, cols, j, skills, a.exp, a.cgpa)
            print(f"  {j['job_id']} {j['title']:<22} skill match {mt:>3.0f}%   selection probability {p:.0%}   missing: {sorted(set(j['required_skills'])-set(skills))}")

if __name__ == "__main__":
    main()
