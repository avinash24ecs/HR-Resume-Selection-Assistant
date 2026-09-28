/**
 * HR Resume Selection Assistant - Native Node.js Server
 * Zero dependencies required. Works natively with Node.js v14+!
 * Run: node server.js
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = process.env.PORT || 5000;
const ROOT = __dirname;

// Load Data
let jobs = [];
let resumes = [];
let miningResults = {};

try {
  jobs = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'jobs.json'), 'utf8'));
} catch (e) {
  console.warn('[Data] Warning: could not load jobs.json:', e.message);
}

try {
  resumes = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'resumes.json'), 'utf8'));
} catch (e) {
  console.warn('[Data] Warning: could not load resumes.json:', e.message);
}

try {
  miningResults = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'mining_results.json'), 'utf8'));
} catch (e) {
  miningResults = { clusters: [], decision_tree: {}, association_rules: [] };
}

// Tech Skill Taxonomy
const TECH_SKILLS = [
  "Python", "SQL", "Machine Learning", "Deep Learning", "Statistics", "Pandas", "NumPy",
  "Scikit-learn", "TensorFlow", "PyTorch", "Tableau", "Power BI", "Data Visualization",
  "Data Warehousing", "ETL", "NLP", "JavaScript", "TypeScript", "React", "Next.js",
  "Node.js", "Express", "HTML", "CSS", "REST API", "GraphQL", "Java", "Spring Boot",
  "MongoDB", "MySQL", "PostgreSQL", "Neo4j", "Cypher", "Docker", "Kubernetes", "Git",
  "Linux", "AWS", "Azure", "GCP", "Microservices", "Indexing"
];

// Helper: Parse JSON Body
function parseBody(req) {
  return new Promise((resolve) => {
    let body = '';
    req.on('data', chunk => { body += chunk.toString(); });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (e) {
        resolve({});
      }
    });
  });
}

// Helper: Send JSON
function sendJSON(res, data, code = 200) {
  res.writeHead(code, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS'
  });
  res.end(JSON.stringify(data));
}

// Resume Parser
function parseResumeText(text) {
  if (!text) return {};
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  
  // Extract Name
  let name = 'Applicant';
  for (const line of lines.slice(0, 4)) {
    if (!/resume|curriculum|email|phone|skills|summary/i.test(line) && line.split(/\s+/).length <= 4) {
      name = line.replace(/[^a-zA-Z\s]/g, '').trim();
      break;
    }
  }

  const emailMatch = text.match(/[\w\.-]+@[\w\.-]+\.\w+/);
  const email = emailMatch ? emailMatch[0] : `${name.toLowerCase().replace(/\s+/g, '.')}@mail.com`;

  const phoneMatch = text.match(/(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/);
  const phone = phoneMatch ? phoneMatch[0] : '+91 98765 43210';

  let exp = 1.0;
  const expMatch = text.match(/(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)/i);
  if (expMatch) exp = parseFloat(expMatch[1]);

  let cgpa = 7.5;
  const cgpaMatch = text.match(/(?:cgpa|gpa|grade)[:\s]*([0-9]\.[0-9]+)/i);
  if (cgpaMatch) cgpa = parseFloat(cgpaMatch[1]);

  let deg = 'B.Tech';
  if (/m\.sc/i.test(text)) deg = 'M.Sc';
  else if (/mca/i.test(text)) deg = 'MCA';
  else if (/bca/i.test(text)) deg = 'BCA';

  const lower = text.toLowerCase();
  const foundSkills = TECH_SKILLS.filter(s => {
    const re = new RegExp(`\\b${s.toLowerCase()}\\b`, 'i');
    return re.test(lower);
  });

  return {
    name,
    email,
    phone,
    city: 'Mumbai',
    experience_years: exp,
    education: { degree: deg, field: 'Computer Science', cgpa, year: 2023 },
    skills: foundSkills,
    certifications: /aws/i.test(text) ? ['AWS Cloud Practitioner'] : [],
    summary: lines[1] || `${name} with ${exp} yrs experience in ${foundSkills.slice(0, 3).join(', ')}.`
  };
}

// ATS Scorer
function scoreResume(candidate, job) {
  const candSkills = new Set(candidate.skills || []);
  const reqSkills = job.required_skills || [];
  const matched = reqSkills.filter(s => candSkills.has(s));
  const missing = reqSkills.filter(s => !candSkills.has(s));
  const additional = (candidate.skills || []).filter(s => !reqSkills.includes(s));

  const matchPct = Math.round((matched.length / Math.max(reqSkills.length, 1)) * 100);
  const exp = parseFloat(candidate.experience_years || 0);
  const minExp = parseFloat(job.min_experience || 1);
  const expScore = exp >= minExp ? 20 : (exp / minExp) * 20;

  const cgpa = parseFloat(candidate.education?.cgpa || 7.0);
  const cgpaScore = Math.min(20, cgpa * 2.0);

  const atsScore = Math.round(matchPct * 0.6 + expScore + cgpaScore);

  let fitLevel = "Low";
  let recommendation = "Low Fit - Critical Skill / Experience Gaps";
  if (atsScore >= 75 && missing.length <= 1) {
    fitLevel = "High";
    recommendation = "Strong Fit - Recommended for Interview";
  } else if (atsScore >= 58) {
    fitLevel = "Medium";
    recommendation = "Moderate Fit - Technical Screening Advised";
  }

  const interview_questions = [
    {
      topic: matched.length ? `Technical Depth: ${matched[0]}` : "Core Competency",
      question: matched.length ? `How do you handle production optimizations and edge cases using ${matched[0]}?` : "Walk us through your core software design approach."
    },
    {
      topic: missing.length ? `Skill Gap: ${missing[0]}` : "Architecture",
      question: missing.length ? `The role requires ${missing[0]}. What related frameworks prepare you to master this quickly?` : "Explain a complex system failure you debugged."
    },
    {
      topic: "System Design & Collaboration",
      question: "Describe how you resolve technical disagreements when architecting high-availability solutions."
    }
  ];

  return {
    ats_score: atsScore,
    skill_match_pct: matchPct,
    matched_skills: matched,
    missing_skills: missing,
    additional_skills: additional,
    fit_level: fitLevel,
    recommendation,
    interview_questions
  };
}

// Request Handler
const server = http.createServer(async (req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;
  const method = req.method;

  // CORS Pre-flight
  if (method === 'OPTIONS') {
    res.writeHead(200, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type,Authorization',
      'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS'
    });
    return res.end();
  }

  // Static Assets / Dashboard
  if (pathname === '/' || pathname === '/index.html') {
    const htmlPath = path.join(ROOT, 'public', 'index.html');
    fs.readFile(htmlPath, (err, content) => {
      if (err) {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        return res.end('Error loading dashboard: ' + err.message);
      }
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(content);
    });
    return;
  }

  // Health
  if (pathname === '/health' || pathname === '/api/health') {
    return sendJSON(res, {
      status: 'ok',
      engine: 'Node.js Native Server',
      mongo: 'in-memory active',
      neo4j: 'python/js fallback active',
      resumes: resumes.length,
      jobs: jobs.length
    });
  }

  // Jobs Endpoints
  if (pathname === '/api/jobs') {
    if (method === 'GET') {
      return sendJSON(res, jobs);
    }
    if (method === 'POST') {
      const payload = await parseBody(req);
      const newJob = {
        job_id: payload.job_id || `J00${jobs.length + 1}`,
        title: payload.title || 'New Position',
        department: payload.department || 'Engineering',
        required_skills: payload.required_skills || ['Python', 'SQL'],
        min_experience: parseFloat(payload.min_experience || 1),
        min_cgpa: parseFloat(payload.min_cgpa || 6.5),
        location: payload.location || 'Mumbai',
        openings: parseInt(payload.openings || 1)
      };
      jobs.push(newJob);
      return sendJSON(res, { success: true, job: newJob });
    }
  }

  // Resumes Endpoints
  if (pathname === '/api/resumes') {
    if (method === 'GET') {
      let list = [...resumes];
      const jobId = parsedUrl.query.job_id;
      if (jobId && jobId.toUpperCase() !== 'ALL') {
        list = list.filter(r => r.applied_job_id === jobId.toUpperCase());
      }
      const status = parsedUrl.query.status;
      if (status && status.toLowerCase() !== 'all') {
        list = list.filter(r => r.status === status);
      }
      const search = (parsedUrl.query.search || '').toLowerCase();
      if (search) {
        list = list.filter(r => 
          (r.name && r.name.toLowerCase().includes(search)) ||
          (r.candidate_id && r.candidate_id.toLowerCase().includes(search)) ||
          (r.skills && r.skills.some(s => s.toLowerCase().includes(search)))
        );
      }
      return sendJSON(res, { total: list.length, resumes: list.slice(0, 200) });
    }
    if (method === 'POST') {
      const payload = await parseBody(req);
      const candId = payload.candidate_id || `C${resumes.length + 101}`;
      const newCand = {
        candidate_id: candId,
        name: payload.name || 'Candidate',
        email: payload.email || `${candId.toLowerCase()}@mail.com`,
        phone: payload.phone || '+91 98765 43210',
        city: payload.city || 'Mumbai',
        education: payload.education || { degree: 'B.Tech', field: 'Computer Science', cgpa: 7.5, year: 2024 },
        experience_years: parseFloat(payload.experience_years || 1.0),
        skills: payload.skills || [],
        applied_job_id: payload.applied_job_id || 'J001',
        status: payload.status || 'Applied',
        expected_salary_lpa: parseFloat(payload.expected_salary_lpa || 6.5)
      };
      resumes.unshift(newCand);
      return sendJSON(res, { success: true, candidate: newCand });
    }
  }

  // Update Resume Status (PATCH /api/resumes/:id)
  const resumeMatch = pathname.match(/^\/api\/resumes\/([A-Za-z0-9]+)$/);
  if (resumeMatch && method === 'PATCH') {
    const candId = resumeMatch[1].toUpperCase();
    const payload = await parseBody(req);
    const cand = resumes.find(r => r.candidate_id === candId);
    if (!cand) return sendJSON(res, { error: 'Candidate not found' }, 404);
    if (payload.status) cand.status = payload.status;
    if (payload.notes) cand.notes = payload.notes;
    if (payload.rating) cand.rating = payload.rating;
    return sendJSON(res, { success: true, candidate_id: candId, candidate: cand });
  }

  // Parse Resume
  if (pathname === '/api/parse_resume' && method === 'POST') {
    const payload = await parseBody(req);
    const parsed = parseResumeText(payload.text || '');
    return sendJSON(res, parsed);
  }

  // Score Resume
  if (pathname === '/api/score_resume' && method === 'POST') {
    const payload = await parseBody(req);
    const scored = scoreResume(payload.candidate || {}, payload.job || {});
    return sendJSON(res, scored);
  }

  // Rank Candidates for Job
  const rankMatch = pathname.match(/^\/api\/rank\/([A-Za-z0-9]+)$/);
  if (rankMatch) {
    const jobId = rankMatch[1].toUpperCase();
    const job = jobs.find(j => j.job_id === jobId);
    if (!job) return sendJSON(res, { error: 'Job not found' }, 404);
    const scored = resumes.map(c => {
      const s = scoreResume(c, job);
      return {
        candidate_id: c.candidate_id,
        name: c.name,
        score: s.ats_score,
        matched: s.matched_skills,
        experience_years: c.experience_years,
        cgpa: c.education?.cgpa || 7.0,
        status: c.status
      };
    }).sort((a, b) => b.score - a.score).slice(0, 15);
    return sendJSON(res, scored);
  }

  // Skills Top
  if (pathname === '/api/skills/top') {
    const counts = {};
    resumes.forEach(r => {
      (r.skills || []).forEach(s => counts[s] = (counts[s] || 0) + 1);
    });
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([k, v]) => ({ skill: k, candidates: v }));
    return sendJSON(res, top);
  }

  // Warehouse Analytics
  if (pathname === '/api/warehouse') {
    const deptRollup = {};
    jobs.forEach(j => {
      const apps = resumes.filter(c => c.applied_job_id === j.job_id);
      const hired = apps.filter(c => c.status === 'Hired').length;
      deptRollup[j.department] = deptRollup[j.department] || { apps: 0, hired: 0 };
      deptRollup[j.department].apps += apps.length;
      deptRollup[j.department].hired += hired;
    });

    return sendJSON(res, {
      "ROLL-UP: applications & hire rate by department": {
        columns: ["department", "apps", "hired", "hire_pct"],
        rows: Object.entries(deptRollup).map(([d, x]) => [d, x.apps, x.hired, Math.round(x.hired / Math.max(x.apps, 1) * 100)])
      }
    });
  }

  // Data Mining
  if (pathname === '/api/mining') {
    return sendJSON(res, miningResults);
  }

  // Graph Endpoints
  if (pathname === '/api/graph/gap') {
    const candId = (parsedUrl.query.candidate || 'C001').toUpperCase();
    const jobId = (parsedUrl.query.job || 'J004').toUpperCase();
    const c = resumes.find(r => r.candidate_id === candId);
    const j = jobs.find(job => job.job_id === jobId);
    if (!c || !j) return sendJSON(res, { error: 'Unknown candidate or job' }, 404);
    const missing = (j.required_skills || []).filter(s => !(c.skills || []).includes(s));
    return sendJSON(res, {
      source: "node-graph-engine",
      results: [{ name: c.name, missing_skills: missing }]
    });
  }

  if (pathname === '/api/graph/related') {
    const seed = parsedUrl.query.skill || 'Neo4j';
    const counts = {};
    resumes.forEach(r => {
      if ((r.skills || []).includes(seed)) {
        r.skills.forEach(s => {
          if (s !== seed) counts[s] = (counts[s] || 0) + 1;
        });
      }
    });
    const results = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([k, v]) => ({ skill: k, together: v }));
    return sendJSON(res, { source: "node-graph-engine", results });
  }

  // 404
  sendJSON(res, { error: 'Not found' }, 404);
});

server.listen(PORT, () => {
  console.log(`======================================================================`);
  console.log(`  HR Resume Selection Assistant - Server Active`);
  console.log(`  URL: http://localhost:${PORT}`);
  console.log(`  Loaded ${resumes.length} candidates, ${jobs.length} jobs`);
  console.log(`======================================================================`);
});
