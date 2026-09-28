"""Pre-computes the scikit-learn mining results into data/mining_results.json so the light web API
(Vercel) can serve them without installing scikit-learn.  Run:  python build_snapshot.py"""
import json, itertools
from collections import Counter
import mining
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

resumes, jobs = mining.load(); df = mining.features(resumes, jobs)
cols = ["experience", "cgpa", "skill_count", "match_pct"]
df["cluster"] = KMeans(n_clusters=3, n_init=10, random_state=42).fit_predict(StandardScaler().fit_transform(df[cols]))
df["hired"] = df.status.eq("Hired")
prof = df.groupby("cluster")[cols + ["salary"]].mean().round(2)
prof["size"] = df.cluster.value_counts().sort_index(); prof["hired_pct"] = (df.groupby("cluster").hired.mean() * 100).round(1)
clusters = [{"cluster": int(i), **{k: float(v) for k, v in r.items()}} for i, r in prof.iterrows()]

fc = ["experience", "cgpa", "skill_count", "certs", "match_pct"]; y = (df.status != "Rejected").astype(int)
Xtr, Xte, ytr, yte = train_test_split(df[fc], y, test_size=0.25, random_state=1, stratify=y)
clf = DecisionTreeClassifier(max_depth=3, random_state=1).fit(Xtr, ytr)
tree = {"accuracy_pct": round(100 * accuracy_score(yte, clf.predict(Xte)), 1),
        "importance": {c: round(float(v), 2) for c, v in zip(fc, clf.feature_importances_)},
        "rules": export_text(clf, feature_names=fc)}

tx = [set(r["skills"]) for r in resumes if r["status"] == "Hired"]; n = len(tx)
one = Counter(s for t in tx for s in t); pair = Counter(p for t in tx for p in itertools.combinations(sorted(t), 2))
rules = []
for (a, b), c in pair.items():
    if c / n < 0.12: continue
    for x, z in ((a, b), (b, a)):
        cf = c / one[x]
        if cf >= 0.6: rules.append({"if": x, "then": z, "support": round(c / n, 2), "confidence": round(cf, 2), "lift": round(cf / (one[z] / n), 2)})
rules.sort(key=lambda r: -r["lift"])
json.dump({"clusters": clusters, "decision_tree": tree, "association_rules": rules[:12], "hired_sample_size": n},
          open("data/mining_results.json", "w"), indent=2)
print("Wrote data/mining_results.json | tree accuracy", tree["accuracy_pct"], "%")
