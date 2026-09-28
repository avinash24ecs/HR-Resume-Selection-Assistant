"""MODULE 4 - Data mining: TF-IDF matching, K-Means clustering, Decision-Tree shortlist prediction,
association rules on skills. Reads from the star schema / MongoDB."""
import json, itertools
from collections import Counter
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

def load():
    return json.load(open("data/resumes.json")), json.load(open("data/jobs.json"))

def tfidf_match(resumes, jobs, job_id="J002", top=5):
    """Text mining: cosine similarity between job requirements and resume text."""
    job = next(j for j in jobs if j["job_id"] == job_id)
    docs = [" ".join(s.replace(" ", "_") for s in r["skills"]) + " " + r["summary"] for r in resumes]
    query = " ".join(s.replace(" ", "_") for s in job["required_skills"])
    vec = TfidfVectorizer(token_pattern=r"[\w\.\+#]+"); X = vec.fit_transform(docs + [query])
    sims = cosine_similarity(X[-1], X[:-1]).ravel()
    print(f"\n>> TF-IDF / cosine ranking for {job['title']}")
    for i in sims.argsort()[::-1][:top]:
        print(f"   {resumes[i]['candidate_id']} {resumes[i]['name']:<20} similarity={sims[i]:.3f}")

def features(resumes, jobs):
    jr = {j["job_id"]: set(j["required_skills"]) for j in jobs}
    rows = []
    for r in resumes:
        req = jr[r["applied_job_id"]]
        rows.append({"candidate_id": r["candidate_id"], "experience": r["experience_years"], "cgpa": r["education"]["cgpa"],
                     "skill_count": len(r["skills"]), "certs": len(r["certifications"]),
                     "match_pct": 100 * len(req & set(r["skills"])) / len(req),
                     "salary": r["expected_salary_lpa"], "status": r["status"]})
    return pd.DataFrame(rows)

def clustering(df, k=3):
    """Clustering: segment candidates into talent pools."""
    cols = ["experience", "cgpa", "skill_count", "match_pct"]
    df = df.copy(); df["cluster"] = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(StandardScaler().fit_transform(df[cols]))
    prof = df.groupby("cluster")[cols + ["salary"]].mean().round(2); prof["size"] = df.cluster.value_counts().sort_index()
    prof["hired_%"] = (df.assign(h=df.status.eq("Hired")).groupby("cluster").h.mean() * 100).round(1)
    print("\n>> K-Means talent segments (cluster profiles)"); print(prof.to_string())
    return df

def classification(df):
    """Classification: predict Shortlisted/Hired (1) vs Rejected (0)."""
    cols = ["experience", "cgpa", "skill_count", "certs", "match_pct"]
    y = (df.status != "Rejected").astype(int)
    Xtr, Xte, ytr, yte = train_test_split(df[cols], y, test_size=0.25, random_state=1, stratify=y)
    clf = DecisionTreeClassifier(max_depth=3, random_state=1).fit(Xtr, ytr)
    print(f"\n>> Decision Tree: predict selection  | accuracy = {accuracy_score(yte, clf.predict(Xte)):.2%}")
    print(classification_report(yte, clf.predict(Xte), target_names=["Rejected", "Selected"], zero_division=0))
    print("Feature importance:", {c: round(float(v), 2) for c, v in zip(cols, clf.feature_importances_)})
    print("Learned rules:\n" + export_text(clf, feature_names=cols))
    return clf, cols

def predict_new(clf, cols, job, skills, exp, cgpa, certs=0):
    req = set(job["required_skills"]); m = 100 * len(req & set(skills)) / len(req)
    p = clf.predict_proba(pd.DataFrame([[exp, cgpa, len(skills), certs, m]], columns=cols))[0][1]
    return p, m

def association_rules(resumes, min_sup=0.12, min_conf=0.6, top=8):
    """Association rule mining (Apriori-style, pairs): skill A => skill B, on HIRED candidates."""
    tx = [set(r["skills"]) for r in resumes if r["status"] == "Hired"]; n = len(tx)
    single = Counter(s for t in tx for s in t)
    pair = Counter(p for t in tx for p in itertools.combinations(sorted(t), 2))
    rules = []
    for (a, b), c in pair.items():
        sup = c / n
        if sup < min_sup: continue
        for x, y in ((a, b), (b, a)):
            conf = c / single[x]; lift = conf / (single[y] / n)
            if conf >= min_conf: rules.append((x, y, sup, conf, lift))
    rules.sort(key=lambda r: (-r[4], -r[3]))
    print(f"\n>> Association rules among {n} hired candidates (support>={min_sup}, confidence>={min_conf})")
    for x, y, s, c, l in rules[:top]:
        print(f"   {x:<18} => {y:<18} support={s:.2f} confidence={c:.2f} lift={l:.2f}")

def run():
    resumes, jobs = load(); df = features(resumes, jobs)
    tfidf_match(resumes, jobs); clustering(df)
    clf, cols = classification(df); association_rules(resumes)
    p, m = predict_new(clf, cols, jobs[3], ["SQL", "MongoDB", "Neo4j", "ETL"], 2, 8.2, 1)
    print(f"\n>> New applicant for Database Engineer: skill match {m:.0f}% -> selection probability {p:.0%}")

if __name__ == "__main__":
    run()
