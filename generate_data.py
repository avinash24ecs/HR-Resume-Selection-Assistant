"""Generates synthetic JSON data: data/jobs.json and data/resumes.json"""
import json, random
from datetime import date, timedelta
random.seed(42)

SKILLS = {
 "Data":     ["Python","SQL","Machine Learning","Pandas","Data Visualization","Statistics","Tableau","Power BI"],
 "Web":      ["JavaScript","React","Node.js","HTML","CSS","MongoDB","REST API","TypeScript"],
 "Backend":  ["Java","Spring Boot","MySQL","Docker","Microservices","Git","Linux","AWS"],
 "Database": ["Neo4j","MongoDB","PostgreSQL","Data Warehousing","ETL","SQL","Cypher","Indexing"],
}
JOBS = [
 ("J001","Data Scientist","Analytics",["Python","Machine Learning","Statistics","Pandas","SQL"],2,7.0,"Mumbai"),
 ("J002","Full Stack Developer","Engineering",["JavaScript","React","Node.js","MongoDB","REST API"],1,6.5,"Pune"),
 ("J003","Backend Engineer","Engineering",["Java","Spring Boot","MySQL","Docker","Git"],2,6.5,"Bengaluru"),
 ("J004","Database Engineer","IT",["SQL","MongoDB","Neo4j","ETL","Data Warehousing"],1,7.0,"Mumbai"),
 ("J005","BI Analyst","Analytics",["SQL","Tableau","Power BI","Data Visualization","Statistics"],1,6.0,"Hyderabad"),
]
FIRST = ["Aarav","Vivaan","Aditya","Ananya","Diya","Ishaan","Kavya","Rohan","Sneha","Priya","Rahul","Neha",
         "Arjun","Meera","Karan","Pooja","Siddharth","Tanvi","Yash","Riya","Manish","Sakshi","Nikhil","Isha"]
LAST = ["Sharma","Patil","Deshmukh","Iyer","Nair","Gupta","Khan","Joshi","Reddy","Mehta","Singh","Kulkarni"]
CITIES = ["Mumbai","Pune","Bengaluru","Hyderabad","Delhi","Kalyan","Thane"]
DEGREES = [("B.Tech","Computer Science"),("B.Tech","Information Technology"),("BCA","Computer Applications"),
           ("MCA","Computer Applications"),("M.Sc","Data Science"),("B.E.","Electronics")]
CERTS = ["AWS Cloud Practitioner","MongoDB Associate Developer","Neo4j Certified Professional",
         "Google Data Analytics","Oracle SQL Associate","Azure Fundamentals"]

def make():
    json.dump([dict(job_id=j[0],title=j[1],department=j[2],required_skills=j[3],min_experience=j[4],
                    min_cgpa=j[5],location=j[6],openings=random.randint(1,4)) for j in JOBS],
              open("data/jobs.json","w"),indent=2)
    resumes=[]
    for i in range(1,121):
        job = random.choice(JOBS)
        track = random.choice(list(SKILLS))
        pool = SKILLS[track]
        skills = set(random.sample(pool, random.randint(3,6)))
        if random.random() < 0.55:                       # many candidates apply near their target job
            skills |= set(random.sample(job[3], random.randint(2,5)))
        if random.random() < 0.4:
            skills |= set(random.sample(sum(SKILLS.values(),[]), 2))
        exp = round(max(0, random.gauss(2.5, 2)),1)
        cgpa = round(min(10, max(5, random.gauss(7.4, 1))),1)
        deg, fld = random.choice(DEGREES)
        match = len(skills & set(job[3])) / len(job[3])
        score = 0.55*match + 0.25*min(exp/job[4],1.5)/1.5 + 0.20*(cgpa/10)
        p = score + random.gauss(0, 0.05)
        status = "Hired" if p > 0.62 else "Shortlisted" if p > 0.5 else "Rejected"
        name = f"{random.choice(FIRST)} {random.choice(LAST)}"
        resumes.append({
          "candidate_id": f"C{i:03d}", "name": name,
          "email": f"{name.lower().replace(' ','.')}{i}@mail.com",
          "city": random.choice(CITIES),
          "education": {"degree": deg, "field": fld, "cgpa": cgpa, "year": random.randint(2015,2025)},
          "experience_years": exp,
          "skills": sorted(skills),
          "certifications": random.sample(CERTS, random.randint(0,2)),
          "projects": [{"title": f"Project {k+1}", "tech": random.sample(sorted(skills), min(2,len(skills)))}
                       for k in range(random.randint(1,3))],
          "summary": f"{deg} {fld} graduate with {exp} years experience in " + ", ".join(sorted(skills)[:4]) + ".",
          "expected_salary_lpa": round(3 + exp*1.8 + random.uniform(0,3),1),
          "applied_job_id": job[0],
          "applied_on": str(date(2025,1,1)+timedelta(days=random.randint(0,364))),
          "status": status,
        })
    json.dump(resumes, open("data/resumes.json","w"), indent=2)
    print(f"Generated {len(resumes)} resumes and {len(JOBS)} jobs in data/*.json")

if __name__ == "__main__":
    make()
