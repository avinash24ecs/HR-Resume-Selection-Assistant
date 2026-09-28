// Top candidates for a job (graph skill match)

MATCH (j:Job {job_id:$job})-[:REQUIRES]->(s:Skill)
WITH j, count(s) AS total
MATCH (c:Candidate)-[:APPLIED_FOR]->(j)
OPTIONAL MATCH (c)-[:HAS_SKILL]->(s2:Skill)<-[:REQUIRES]-(j)
WITH c, total, count(s2) AS matched
RETURN c.candidate_id AS id, c.name AS name, matched, total, round(100.0*matched/total) AS match_pct
ORDER BY matched DESC, c.experience DESC LIMIT 5;

// Skill gap of a candidate for a job

MATCH (c:Candidate {candidate_id:$cand}), (j:Job {job_id:$job})-[:REQUIRES]->(s:Skill)
WHERE NOT (c)-[:HAS_SKILL]->(s)
RETURN c.name AS name, collect(s.name) AS missing_skills;

// Skills most often paired with Neo4j (recommendation)

MATCH (:Skill {name:'Neo4j'})-[r:CO_OCCURS]-(o:Skill)
RETURN o.name AS skill, r.weight AS together ORDER BY together DESC LIMIT 5;

// Most in-demand skills across candidates

MATCH (:Candidate)-[:HAS_SKILL]->(s:Skill)
RETURN s.name AS skill, count(*) AS candidates ORDER BY candidates DESC LIMIT 5;