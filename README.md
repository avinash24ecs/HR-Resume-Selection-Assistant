# HR Resume Selection Assistant (ADBMS Mini Project)

Screens resumes for job openings using **JSON -> MongoDB -> Neo4j -> Data Warehouse -> Data Mining**.

```
data/*.json        generated resumes & jobs (JSON documents), mining_results.json (pre-computed)
mongo_ops.py       MongoDB: load JSON, indexes, CRUD, queries, aggregation, candidate scoring pipeline
neo4j_graph.py     Neo4j graph (Candidate-HAS_SKILL->Skill<-REQUIRES-Job, CO_OCCURS) + Cypher analysis
warehouse.py       ETL Mongo -> star schema (SQLite) + OLAP roll-up/drill-down/slice/dice/pivot
mining.py          TF-IDF, K-Means, Decision Tree, association rules (scikit-learn)
build_snapshot.py  pre-computes mining results for the web API
api/index.py       Flask API (Vercel serverless function)
public/index.html  dashboard (served by Vercel as a static file)
main.py            command-line interface
```

## A. Run locally (command line, full features)
```
pip install -r requirements-full.txt
python main.py all
python main.py rank J004 --top 5
python main.py match "SQL,MongoDB,Python" --exp 2 --cgpa 8
```
MongoDB / Neo4j are optional locally: if not running, an in-memory MongoDB and a Python fallback are used.

## B. Run the web app locally
```
pip install -r requirements.txt
python api/index.py          # open http://localhost:5000
```

## C. Deploy on Vercel via Git
1. Create a GitHub repo and push this whole folder (`git init && git add . && git commit -m "hr assistant" && git push`).
2. On vercel.com: **Add New > Project**, import the repo. Leave Framework Preset as "Other". No build command needed. Deploy.
3. Open the URL. `/health` should return `status: ok`. That's it - it works with no databases (in-memory MongoDB).

### Optional: connect real databases (Project > Settings > Environment Variables, then redeploy)
| Variable | Value |
|---|---|
| `MONGO_URI` | MongoDB Atlas connection string (`mongodb+srv://...`). Data is auto-seeded on first request if the DB is empty. In Atlas allow network access from anywhere (0.0.0.0/0) because Vercel IPs change. |
| `NEO4J_URI` | Aura URI, e.g. `neo4j+s://xxxx.databases.neo4j.io` |
| `NEO4J_USER` | `neo4j` |
| `NEO4J_PASSWORD` | Aura password |

Load the graph into Aura once from your laptop:
```
pip install -r requirements-full.txt
set NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io   (Mac/Linux: export ...)
set NEO4J_USER=neo4j
set NEO4J_PASSWORD=your-password
python main.py graph
```
If Neo4j is not configured or unreachable, the graph endpoints answer from a Python fallback and say so (`"source"` field).

## API
`/health` `/api/jobs` `/api/rank/<job_id>?top=10` `/api/search?skills=Python,SQL&min_exp=2&min_cgpa=7.5&city=Mumbai`
`/api/skills/top` `/api/match?skills=SQL,MongoDB&exp=2&cgpa=8` `/api/warehouse` `/api/mining`
`/api/graph/related?skill=Neo4j` `/api/graph/gap?candidate=C001&job=J004` `/api/graph/match?job=J004`

## Notes
- Serverless has no persistent disk, so the web app builds the star-schema warehouse in memory on each cold start and reads mining results from `data/mining_results.json` (re-create with `python build_snapshot.py`).
- All data is synthetic sample data.
