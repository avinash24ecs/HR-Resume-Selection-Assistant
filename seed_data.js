/**
 * HR Resume Selection Assistant - Data Seeder & Generator
 * Generates rich, realistic candidate profiles and job requisitions.
 * Run: node seed_data.js [count] (default: 250)
 * Example: node seed_data.js 300
 */
const fs = require('fs');
const path = require('path');

const countArg = parseInt(process.argv[2], 10);
const TARGET_COUNT = !isNaN(countArg) && countArg > 0 ? countArg : 250;

console.log("======================================================================");
console.log(`  Seeding Data for HR Resume Selection Assistant (${TARGET_COUNT} candidates)`);
console.log("======================================================================\n");

// Expanded Job Requisitions (10 Departments & Roles)
const JOBS = [
  {
    job_id: "J001",
    title: "Data Scientist",
    department: "Analytics",
    required_skills: ["Python", "Machine Learning", "Statistics", "Pandas", "SQL"],
    min_experience: 2.0,
    min_cgpa: 7.0,
    location: "Mumbai",
    openings: 3
  },
  {
    job_id: "J002",
    title: "Full Stack Developer",
    department: "Engineering",
    required_skills: ["JavaScript", "React", "Node.js", "MongoDB", "REST API"],
    min_experience: 1.0,
    min_cgpa: 6.5,
    location: "Pune",
    openings: 4
  },
  {
    job_id: "J003",
    title: "Backend Engineer",
    department: "Engineering",
    required_skills: ["Java", "Spring Boot", "MySQL", "Docker", "Git"],
    min_experience: 2.0,
    min_cgpa: 6.5,
    location: "Bengaluru",
    openings: 5
  },
  {
    job_id: "J004",
    title: "Database Engineer",
    department: "IT",
    required_skills: ["SQL", "MongoDB", "Neo4j", "ETL", "Data Warehousing"],
    min_experience: 1.0,
    min_cgpa: 7.0,
    location: "Mumbai",
    openings: 2
  },
  {
    job_id: "J005",
    title: "BI Analyst",
    department: "Analytics",
    required_skills: ["SQL", "Tableau", "Power BI", "Data Visualization", "Statistics"],
    min_experience: 1.0,
    min_cgpa: 6.0,
    location: "Hyderabad",
    openings: 3
  },
  {
    job_id: "J006",
    title: "Cloud DevOps Engineer",
    department: "Infrastructure",
    required_skills: ["Docker", "Kubernetes", "AWS", "Linux", "CI/CD", "Git"],
    min_experience: 2.5,
    min_cgpa: 6.5,
    location: "Bengaluru",
    openings: 4
  },
  {
    job_id: "J007",
    title: "AI / Deep Learning Engineer",
    department: "AI Research",
    required_skills: ["Python", "TensorFlow", "PyTorch", "Deep Learning", "NLP", "Machine Learning"],
    min_experience: 2.0,
    min_cgpa: 7.5,
    location: "Hyderabad",
    openings: 2
  },
  {
    job_id: "J008",
    title: "Frontend Architect",
    department: "Engineering",
    required_skills: ["React", "TypeScript", "JavaScript", "Next.js", "HTML", "CSS"],
    min_experience: 3.0,
    min_cgpa: 6.8,
    location: "Pune",
    openings: 2
  }
];

// Taxonomy of skills
const SKILL_POOLS = {
  Data: ["Python", "SQL", "Machine Learning", "Pandas", "NumPy", "Statistics", "Tableau", "Power BI", "Data Visualization"],
  Web: ["JavaScript", "TypeScript", "React", "Next.js", "Node.js", "Express", "HTML", "CSS", "REST API", "GraphQL"],
  Backend: ["Java", "Spring Boot", "MySQL", "PostgreSQL", "MongoDB", "Microservices", "Git", "Linux"],
  Database: ["SQL", "MongoDB", "Neo4j", "Cypher", "ETL", "Data Warehousing", "Indexing", "PostgreSQL"],
  DevOps: ["Docker", "Kubernetes", "AWS", "Azure", "GCP", "Linux", "Git", "CI/CD"],
  AI: ["Python", "Deep Learning", "TensorFlow", "PyTorch", "NLP", "Scikit-learn", "Machine Learning"]
};

const ALL_SKILLS = Array.from(new Set(Object.values(SKILL_POOLS).flat()));

const FIRST_NAMES = [
  "Aarav", "Vivaan", "Aditya", "Ananya", "Diya", "Ishaan", "Kavya", "Rohan", "Sneha", "Priya",
  "Rahul", "Neha", "Arjun", "Meera", "Karan", "Pooja", "Siddharth", "Tanvi", "Yash", "Riya",
  "Manish", "Sakshi", "Nikhil", "Isha", "Deepak", "Vikram", "Simran", "Varun", "Shruti", "Tarun"
];

const LAST_NAMES = [
  "Sharma", "Patil", "Deshmukh", "Iyer", "Nair", "Gupta", "Khan", "Joshi", "Reddy", "Mehta",
  "Singh", "Kulkarni", "Verma", "Chopra", "Bose", "Menon", "Sen", "Pillai", "Das", "Rao"
];

const CITIES = ["Mumbai", "Bengaluru", "Pune", "Hyderabad", "Delhi NCR", "Chennai", "Kolkata", "Ahmedabad"];

const DEGREES = [
  { degree: "B.Tech", field: "Computer Science" },
  { degree: "B.Tech", field: "Information Technology" },
  { degree: "B.E.", field: "Electronics & Telecommunication" },
  { degree: "M.Tech", field: "Software Systems" },
  { degree: "M.Sc", field: "Data Science & AI" },
  { degree: "MCA", field: "Computer Applications" },
  { degree: "BCA", field: "Computer Applications" }
];

const CERTS = [
  "AWS Certified Solutions Architect", "AWS Cloud Practitioner", "MongoDB Associate Developer",
  "Neo4j Certified Professional", "Google Professional Data Engineer", "Azure Fundamentals",
  "Docker Certified Associate", "Kubernetes CKA", "Oracle SQL Associate"
];

function randChoice(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randSample(arr, n) {
  const shuffled = [...arr].sort(() => 0.5 - Math.random());
  return shuffled.slice(0, Math.min(n, arr.length));
}

function randGaussian(mean, stdev) {
  let u = 1 - Math.random();
  let v = Math.random();
  let z = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
  return mean + z * stdev;
}

// Generate Candidates
const resumes = [];
for (let i = 1; i <= TARGET_COUNT; i++) {
  const targetJob = randChoice(JOBS);
  const trackName = randChoice(Object.keys(SKILL_POOLS));
  const trackSkills = SKILL_POOLS[trackName];

  // Candidates often have core track skills + job skills + extra
  let candSkills = new Set(randSample(trackSkills, Math.floor(Math.random() * 4) + 3));
  if (Math.random() < 0.65) {
    const jobSample = randSample(targetJob.required_skills, Math.floor(Math.random() * 4) + 2);
    jobSample.forEach(s => candSkills.add(s));
  }
  if (Math.random() < 0.45) {
    randSample(ALL_SKILLS, 2).forEach(s => candSkills.add(s));
  }

  const exp = Math.max(0, Math.round(randGaussian(2.8, 1.8) * 10) / 10);
  const cgpa = Math.min(10.0, Math.max(5.5, Math.round(randGaussian(7.5, 0.9) * 10) / 10));
  const degObj = randChoice(DEGREES);
  const name = `${randChoice(FIRST_NAMES)} ${randChoice(LAST_NAMES)}`;
  const candId = `C${String(i).padStart(3, '0')}`;

  // Selection likelihood
  const matched = targetJob.required_skills.filter(s => candSkills.has(s));
  const matchPct = (matched.length / targetJob.required_skills.length) * 100;
  const score = matchPct * 0.6 + (exp >= targetJob.min_experience ? 20 : (exp / targetJob.min_experience) * 20) + (cgpa * 2);

  let status = "Applied";
  let rating = 3;
  if (score >= 76) {
    status = Math.random() < 0.6 ? "Hired" : "Shortlisted";
    rating = status === "Hired" ? 5 : 4;
  } else if (score >= 58) {
    status = Math.random() < 0.5 ? "Shortlisted" : "Interview";
    rating = 4;
  } else {
    status = Math.random() < 0.7 ? "Rejected" : "Applied";
    rating = status === "Rejected" ? 2 : 3;
  }

  const salaryLpa = Math.round((4.0 + exp * 2.2 + (status === 'Hired' ? 2.5 : 0) + (Math.random() * 2)) * 10) / 10;
  const skillsArray = Array.from(candSkills);

  resumes.push({
    candidate_id: candId,
    name,
    email: `${name.toLowerCase().replace(/\s+/g, '.')}${i}@mail.com`,
    phone: `+91 ${Math.floor(9000000000 + Math.random() * 999999999)}`,
    city: randChoice(CITIES),
    education: {
      degree: degObj.degree,
      field: degObj.field,
      cgpa,
      year: 2025 - Math.floor(exp) - Math.floor(Math.random() * 2)
    },
    experience_years: exp,
    skills: skillsArray.sort(),
    certifications: exp > 1.5 && Math.random() < 0.6 ? randSample(CERTS, Math.floor(Math.random() * 2) + 1) : [],
    projects: [
      {
        title: `Enterprise ${trackName} System`,
        tech: randSample(skillsArray, Math.min(2, skillsArray.length))
      }
    ],
    summary: `${degObj.degree} in ${degObj.field} with ${exp} yrs experience in ${skillsArray.slice(0, 4).join(', ')}.`,
    expected_salary_lpa: salaryLpa,
    applied_job_id: targetJob.job_id,
    applied_on: `2025-${String(Math.floor(Math.random() * 12) + 1).padStart(2, '0')}-${String(Math.floor(Math.random() * 28) + 1).padStart(2, '0')}`,
    status,
    rating,
    notes: status === 'Hired' ? 'Aced technical round, strong cultural fit' : status === 'Shortlisted' ? 'Strong candidate profile, recommended for technical interview' : ''
  });
}

// Write to files
const dataDir = path.join(__dirname, 'data');
if (!fs.existsSync(dataDir)) fs.mkdirSync(dataDir, { recursive: true });

fs.writeFileSync(path.join(dataDir, 'jobs.json'), JSON.stringify(JOBS, null, 2));
fs.writeFileSync(path.join(dataDir, 'resumes.json'), JSON.stringify(resumes, null, 2));

console.log(`[Success] Written ${JOBS.length} jobs to data/jobs.json`);
console.log(`[Success] Written ${resumes.length} candidates to data/resumes.json`);
console.log("\nSummary of Generated Database:");
const hiredCount = resumes.filter(r => r.status === 'Hired').length;
const shortCount = resumes.filter(r => r.status === 'Shortlisted').length;
const interviewCount = resumes.filter(r => r.status === 'Interview').length;
const rejectedCount = resumes.filter(r => r.status === 'Rejected').length;
console.log(`  - Total Candidates: ${resumes.length}`);
console.log(`  - Hired:            ${hiredCount} (${Math.round(hiredCount/resumes.length*100)}%)`);
console.log(`  - Shortlisted:      ${shortCount} (${Math.round(shortCount/resumes.length*100)}%)`);
console.log(`  - Interview:        ${interviewCount} (${Math.round(interviewCount/resumes.length*100)}%)`);
console.log(`  - Rejected:         ${rejectedCount} (${Math.round(rejectedCount/resumes.length*100)}%)`);
console.log(`  - Total Job Roles:  ${JOBS.length}`);
console.log("\n======================================================================\n");
