# HR Resume Selection Assistant (ADBMS & Enterprise ATS)

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/avinash24ecs/HR-Resume-Selection-Assistant)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A live, production-grade **HR Resume Selection Assistant & Applicant Tracking System (ATS)** with multi-model database intelligence powered by **JSON Documents -> MongoDB -> Neo4j Graph -> Star Schema Data Warehouse -> Data Mining & Machine Learning**.

---

## 🚀 Quick Launch (3 Ways to Run Live)

### 1. One-Click Windows Launcher (Fastest)
Double-click [`start_app.bat`](start_app.bat) in the root directory.
- Automatically launches the server and opens your browser to `http://localhost:5000`.
- Priority detection: Node.js (instant startup) &rarr; Python Flask &rarr; Zero-Install Standalone browser mode.

### 2. Node.js Live Server (Zero-Dependencies)
```bash
node server.js
```
- Starts native high-speed HTTP server on port 5000. Open `http://localhost:5000`.

### 3. Python Flask Server
```bash
pip install -r requirements.txt
python run_assistant.py
# or: python api/index.py
```

### 4. Zero-Install Standalone Browser Mode
Double-click [`public/index.html`](public/index.html) or open it directly in Chrome, Edge, Firefox, or Safari!
- Works 100% offline with zero installations or external database dependencies.
- Client-side PDF extraction, smart parsing, ATS scoring, candidate database, and OLAP analytics work out-of-the-box.

---

## 🌟 Key Features

```
┌────────────────────────────────────────────────────────────────────────┐
│                   HR RESUME SELECTION ASSISTANT                        │
├─────────────────┬───────────────────┬───────────────────┬──────────────┤
│ 📄 ATS Screener │ 👥 Talent Pool    │ 💼 Job Reqs       │ 🕸️ Graph     │
│ Drag & drop PDF │ 120+ Candidates   │ 5 Roles + Custom  │ Skill Matrix │
│ Batch Leaderboard│ Kanban Pipeline  │ JD Auto-Extractor │ Gap Analysis │
│ Interview Notes │ CSV Export        │ Requisition Stats │ Co-occurrence│
└─────────────────┴───────────────────┴───────────────────┴──────────────┘
```

1. **📄 Live Resume Screener & Smart ATS Parser**:
   - **Upload or Drag & Drop**: Accepts `.pdf`, `.docx`, and `.txt` files or raw text pasting.
   - **Entity Extraction**: Automatically parses Name, Email, Phone, Degree, CGPA, Experience, and Technical Skills.
   - **4 Instant Sample Buttons**: 1-click test buttons for *Data Scientist (Senior)*, *Full Stack Dev (Mid)*, *Database Engineer (Junior)*, and *Fresher Graduate*.
   - **Batch Multi-Resume Screener**: Screen multiple candidates at once into a comparative leaderboard with 1-click bulk shortlisting.
   - **ATS Score Gauge (0–100%)**: Evaluates against 60% skills alignment + 20% experience criteria + 20% academic CGPA.
   - **Strengths vs. Skill Gaps**: Highlights matched skills (green tags) and missing skills (red tags).
   - **Targeted Interview Questions**: Dynamically generates technical and behavioral questions tailored to the candidate's strengths and missing skills.

2. **👥 Talent Pool & Recruitment Pipeline**:
   - 120+ pre-seeded candidate database with instant search, multi-filters (Job opening, status, experience, CGPA).
   - **View Switcher**: Toggle between **Table View** and **Pipeline Kanban Board** (`Applied`, `Shortlisted`, `Interview`, `Hired`, `Rejected`).
   - **Candidate Dossier Modal**: Interactive 5-star rating, interview notes, and status management.
   - **Export to CSV**: Download filtered candidate lists directly into Excel/Google Sheets.
   - **Printable ATS Report**: Clean 1-page evaluation layout for interview panels.

3. **💼 Job Requisitions & Opening Creator**:
   - Manage active job openings (*Data Scientist*, *Full Stack Developer*, *Backend Engineer*, *Database Engineer*, *BI Analyst*).
   - **JD Auto-Extractor**: Paste any job description paragraph to auto-fill title, required skills, and experience benchmarks.

4. **🕸️ Skill Matrix & Neo4j Graph Explorer**:
   - Visualizes candidate skill profiles against job requirements to detect gaps.
   - Explores skill co-occurrence weights (mirroring Neo4j `CO_OCCURS` edge relationships).

5. **📊 OLAP Warehouse & Data Mining**:
   - Star schema reports: Department Funnel Roll-up, Requisition-level Drill-down, and Hire Rate conversions.
   - K-Means candidate segmentation (3 clusters), Decision Tree hiring feature importances, and Association Rules.

6. **⚡ Live REST API Console**:
   - In-app interactive console to test backend endpoints (`/health`, `/api/jobs`, `/api/rank/<id>`, `/api/search`, `/api/warehouse`, `/api/mining`).

---

## 📁 Repository Structure

```
data/
  ├── jobs.json             # Job openings definition
  ├── resumes.json          # 120 synthetic candidate resumes
  ├── mining_results.json   # Pre-computed K-Means & Decision Tree results
  └── sample_resumes/       # Ready-to-test sample resumes (DS, FS, DB, Fresher)
api/
  └── index.py              # Flask REST API (Vercel serverless compatible)
public/
  └── index.html            # Complete SPA dashboard (ATS Screener, Kanban, OLAP)
server.js                   # Native zero-dependency Node.js HTTP server
resume_parser.py            # Python regex & NLP entity extractor & ATS engine
run_assistant.py            # Python launcher with automatic browser opening
start_app.bat               # 1-click Windows launcher
test_suite.js               # Automated verification test suite
vercel.json                 # Vercel deployment configuration
README.md                   # Project documentation
```

---

## 🌐 REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Server and database status |
| `GET` | `/api/jobs` | List all job openings |
| `POST` | `/api/jobs` | Create a new job requisition |
| `GET` | `/api/resumes` | Query candidates with filters and pagination |
| `POST` | `/api/resumes` | Add a new candidate document |
| `PATCH` | `/api/resumes/<id>` | Update candidate status, rating, or notes |
| `POST` | `/api/parse_resume` | Parse raw text into structured profile |
| `POST` | `/api/score_resume` | Compute ATS score, fit, gaps, and interview questions |
| `GET` | `/api/rank/<job_id>` | Rank candidates for a specific job |
| `GET` | `/api/skills/top` | Top 10 most common candidate skills |
| `GET` | `/api/warehouse` | Star schema OLAP roll-up & drill-down metrics |
| `GET` | `/api/mining` | Pre-computed K-Means, Decision Tree & Association Rules |
| `GET` | `/api/graph/gap` | Neo4j Cypher candidate vs job skill gap query |
| `GET` | `/api/graph/related` | Neo4j Cypher skill co-occurrence recommendations |

---

## 🧪 Verification & Testing

Run the automated verification suite:
```bash
node test_suite.js
```
All tests check file integrity, data validation, parser taxonomy, and scoring logic.
