"""Resume Parsing and ATS Scoring Engine for HR Resume Selection Assistant."""
import re
from typing import Dict, List, Any

# Extensive skill taxonomy
TECH_SKILLS = [
    # Data & AI
    "Python", "SQL", "Machine Learning", "Deep Learning", "Statistics", "Pandas", "NumPy",
    "Scikit-learn", "TensorFlow", "PyTorch", "Tableau", "Power BI", "Data Visualization",
    "Data Warehousing", "ETL", "NLP", "Computer Vision", "Data Analysis", "Apache Spark",
    "Big Data", "Hadoop", "Airflow", "R",
    # Web & Full Stack
    "JavaScript", "TypeScript", "React", "React Native", "Next.js", "Vue.js", "Angular",
    "Node.js", "Express", "HTML", "CSS", "Tailwind CSS", "Bootstrap", "REST API", "GraphQL",
    # Backend & Architecture
    "Java", "Spring Boot", "C++", "C#", ".NET", "PHP", "Go", "Rust", "Microservices",
    "System Design", "OOP", "Data Structures", "Algorithms",
    # Databases
    "MongoDB", "MySQL", "PostgreSQL", "Neo4j", "Cypher", "Redis", "Elasticsearch",
    "Cassandra", "Oracle SQL", "Indexing", "NoSQL", "SQLite",
    # Cloud, DevOps & Tools
    "Docker", "Kubernetes", "Git", "GitHub", "GitLab", "Linux", "AWS", "Azure", "GCP",
    "CI/CD", "Jenkins", "Terraform", "Ansible", "Nginx"
]

SKILL_LOOKUP = {s.lower(): s for s in TECH_SKILLS}

def parse_resume_text(text: str) -> Dict[str, Any]:
    """Extracts structured entities from raw resume text."""
    if not text:
        return {}

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # 1. Candidate Name
    name = "Candidate"
    for line in lines[:5]:
        clean = re.sub(r'[^a-zA-Z\s]', '', line).strip()
        words = clean.split()
        if 2 <= len(words) <= 3 and not any(w.lower() in [
            "resume", "curriculum", "vitae", "profile", "contact", "email",
            "phone", "education", "experience", "skills", "summary"
        ] for w in words):
            name = clean
            break

    # 2. Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    email = email_match.group(0) if email_match else f"{name.lower().replace(' ', '.')}@mail.com"

    # 3. Phone
    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    phone = phone_match.group(0) if phone_match else "+91 98765 43210"

    # 4. Degree & Field
    degree = "B.Tech"
    field = "Computer Science"
    degree_patterns = [
        (r'\b(B\.Tech|B\.E\.|Bachelor of Technology|Bachelor of Engineering)\b', "B.Tech", "Computer Science"),
        (r'\b(M\.Tech|M\.E\.|Master of Technology)\b', "M.Tech", "Computer Science"),
        (r'\b(BCA|Bachelor of Computer Applications)\b', "BCA", "Computer Applications"),
        (r'\b(MCA|Master of Computer Applications)\b', "MCA", "Computer Applications"),
        (r'\b(M\.Sc|Master of Science)\b', "M.Sc", "Data Science"),
        (r'\b(B\.Sc|Bachelor of Science)\b', "B.Sc", "Information Technology"),
        (r'\b(MBA)\b', "MBA", "Information Systems"),
    ]
    for pattern, deg, fld in degree_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            degree, field = deg, fld
            break

    # 5. CGPA / Percentage
    cgpa = 7.5
    cgpa_match = re.search(r'(?:cgpa|gpa|grade)[:\s]*([0-9]\.[0-9]+|[0-9]{1,2}(?:\.[0-9]+)?(?:\s*\/\s*10)?)', text, re.IGNORECASE)
    if cgpa_match:
        try:
            val_str = cgpa_match.group(1).split('/')[0].strip()
            val = float(val_str)
            if val <= 10.0:
                cgpa = val
            elif val <= 100:
                cgpa = round(val / 9.5, 1)  # percentage to CGPA approx
        except ValueError:
            pass
    else:
        pct_match = re.search(r'(\d{2}(?:\.\d+)?)\s*%', text)
        if pct_match:
            try:
                cgpa = round(float(pct_match.group(1)) / 9.5, 1)
            except ValueError:
                pass

    # 6. Experience in Years
    exp_years = 1.0
    exp_matches = re.findall(r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s*(?:of)?\s*(?:experience|exp))?', text, re.IGNORECASE)
    if exp_matches:
        try:
            numbers = [float(n) for n in exp_matches if 0 <= float(n) <= 40]
            if numbers:
                exp_years = max(numbers)
        except ValueError:
            pass

    # 7. Skills extraction
    found_skills = set()
    text_lower = text.lower()
    for skill_lower, skill_proper in SKILL_LOOKUP.items():
        # Match as word boundary to prevent partial matches like 'R' in 'React'
        pattern = r'(?<![a-zA-Z0-9])' + re.escape(skill_lower) + r'(?![a-zA-Z0-9])'
        if re.search(pattern, text_lower):
            found_skills.add(skill_proper)

    # 8. Certifications
    certs = []
    cert_catalog = [
        "AWS Cloud Practitioner", "AWS Certified Solutions Architect", "MongoDB Associate Developer",
        "Neo4j Certified Professional", "Google Data Analytics", "Oracle SQL Associate",
        "Azure Fundamentals", "Docker Certified Associate", "Kubernetes CKA"
    ]
    for c in cert_catalog:
        if c.lower() in text_lower:
            certs.append(c)

    # 9. Summary
    summary = ""
    for line in lines:
        if len(line) > 50 and any(w in line.lower() for w in ["developer", "engineer", "scientist", "experience", "passionate", "graduate"]):
            summary = line
            break
    if not summary:
        summary = f"{degree} {field} with {exp_years} yrs experience in {', '.join(sorted(found_skills)[:4])}."

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "city": "Mumbai",
        "education": {
            "degree": degree,
            "field": field,
            "cgpa": round(min(10.0, max(4.0, cgpa)), 1),
            "year": 2024
        },
        "experience_years": exp_years,
        "skills": sorted(list(found_skills)),
        "certifications": certs,
        "summary": summary
    }

def score_candidate_for_job(candidate: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """Computes comprehensive ATS score, fit analysis, and interview questions."""
    cand_skills = set(candidate.get("skills", []))
    req_skills = set(job.get("required_skills", []))
    matched_skills = sorted(list(cand_skills & req_skills))
    missing_skills = sorted(list(req_skills - cand_skills))
    additional_skills = sorted(list(cand_skills - req_skills))

    total_req = len(req_skills) if req_skills else 1
    skill_match_pct = round(len(matched_skills) / total_req * 100, 1)

    exp = float(candidate.get("experience_years", 0))
    min_exp = float(job.get("min_experience", 0))
    exp_ok = exp >= min_exp
    exp_score = 20.0 if exp_ok else round((exp / max(min_exp, 1.0)) * 20.0, 1)

    cgpa = float(candidate.get("education", {}).get("cgpa", 7.0))
    min_cgpa = float(job.get("min_cgpa", 6.5))
    cgpa_ok = cgpa >= min_cgpa
    cgpa_score = round(cgpa * 2.0, 1)  # max 20

    # ATS weighted score: 60% skills + 20% experience + 20% academic/cgpa
    ats_score = round(skill_match_pct * 0.6 + exp_score + cgpa_score, 1)
    ats_score = min(100.0, max(0.0, ats_score))

    # HR Fit Recommendation
    if ats_score >= 78 and len(missing_skills) <= 1:
        recommendation = "Strong Fit - Recommended for Interview"
        fit_level = "High"
    elif ats_score >= 60:
        recommendation = "Moderate Fit - Technical Screening Advised"
        fit_level = "Medium"
    else:
        recommendation = "Low Fit - Critical Skill / Experience Gaps"
        fit_level = "Low"

    # Key Strengths
    strengths = []
    if skill_match_pct >= 80:
        strengths.append(f"High technical skill alignment ({skill_match_pct}% match)")
    if exp > min_exp + 1:
        strengths.append(f"Senior level experience ({exp} yrs vs {min_exp} yrs required)")
    elif exp_ok:
        strengths.append(f"Meets experience criteria ({exp} yrs)")
    if cgpa >= 8.0:
        strengths.append(f"Strong academic background (CGPA: {cgpa}/10)")
    if candidate.get("certifications"):
        strengths.append(f"Certified in {', '.join(candidate['certifications'])}")
    if not strengths:
        strengths.append("Foundational technical competencies present")

    # Key Gaps
    gaps = []
    if missing_skills:
        gaps.append(f"Missing required skills: {', '.join(missing_skills)}")
    if not exp_ok:
        gaps.append(f"Experience deficit: {exp} yrs (Required: {min_exp} yrs)")
    if not cgpa_ok:
        gaps.append(f"CGPA below preferred benchmark: {cgpa} (Min: {min_cgpa})")
    if not gaps:
        gaps.append("None identified - profile meets all baseline requirements")

    # Smart Targeted Interview Questions
    interview_questions = []
    # 1. Matched skills deep-dive
    skill_q_bank = {
        "Python": "How do you handle memory management and GIL limitations in high-concurrency Python applications?",
        "SQL": "Can you explain how you optimize a slow-running SQL query with multiple joins and indexes?",
        "Machine Learning": "How do you address data leakage and class imbalance when training classification models?",
        "Pandas": "Explain vectorization in Pandas and how it compares to iterative row processing with apply.",
        "JavaScript": "Explain the JavaScript Event Loop, microtasks vs macrotasks, and closures.",
        "React": "How do you manage complex global state in React, and when would you avoid useEffect?",
        "Node.js": "How does Node.js handle CPU-intensive tasks without blocking the main event thread?",
        "MongoDB": "How do you design a MongoDB schema for 1-to-many relationships (embedding vs referencing)?",
        "Neo4j": "Explain when a Graph Database like Neo4j outperforms relational databases, and how Cypher traverses paths.",
        "Docker": "How do you optimize Docker image layer caching and minimize production container size?",
        "Java": "Explain the Java garbage collection mechanism and differences between G1 and ZGC.",
        "Spring Boot": "How do dependency injection and bean lifecycles work under the hood in Spring Boot?",
        "ETL": "Describe an end-to-end data pipeline failure scenario you debugged and how you ensured idempotency.",
        "Data Warehousing": "What is the difference between Star Schema and Snowflake Schema, and why choose one for OLAP?"
    }

    for skill in matched_skills[:2]:
        if skill in skill_q_bank:
            interview_questions.append({
                "type": "Technical Validation",
                "topic": skill,
                "question": skill_q_bank[skill]
            })

    # 2. Skill gap exploration question
    if missing_skills:
        gap_skill = missing_skills[0]
        interview_questions.append({
            "type": "Skill Gap Assessment",
            "topic": gap_skill,
            "question": f"The role requires {gap_skill}, which is not prominent in your background. What related tools or projects prepare you to learn and apply {gap_skill} quickly?"
        })

    # 3. Behavioral / Architectural question
    interview_questions.append({
        "type": "System & Problem Solving",
        "topic": "Architecture & Delivery",
        "question": f"Walk us through the most technically challenging project you built using {matched_skills[0] if matched_skills else 'your core tech stack'}. What trade-offs did you make?"
    })

    return {
        "ats_score": ats_score,
        "skill_match_pct": skill_match_pct,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "additional_skills": additional_skills,
        "exp_ok": exp_ok,
        "cgpa_ok": cgpa_ok,
        "fit_level": fit_level,
        "recommendation": recommendation,
        "strengths": strengths,
        "gaps": gaps,
        "interview_questions": interview_questions
    }
