import os
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recommender")

# Load predefined careers list
CAREERS_FILE = os.path.join(os.path.dirname(__file__), "careers.json")
with open(CAREERS_FILE, "r", encoding="utf-8") as f:
    ALL_CAREERS = json.load(f)

# Quick map for easy access
CAREER_MAP = {c["id"]: c for c in ALL_CAREERS}

def recommend_careers_algo(answers, careers, limit=10):
    if not answers:
        return []
    
    scored = []
    for c in careers:
        score = 0
        reasons = []
        
        # Qualification match
        ans_qual = answers.get("qualification", "")
        c_quals = c.get("qualifications", [])
        if ans_qual and c_quals:
            if any(q.lower() in ans_qual.lower() or ans_qual.lower() in q.lower() for q in c_quals):
                score += 15
                reasons.append("Matches your qualification")
                
        # Stream match
        ans_stream = answers.get("stream", "")
        c_streams = c.get("streams", [])
        if ans_stream and c_streams:
            if any(s.lower() == ans_stream.lower() for s in c_streams):
                score += 10
                reasons.append(f"Aligned with {ans_stream} stream")
                
        # Skills match
        ans_skills = [s.lower() for s in answers.get("skills", [])]
        c_skills = [s.lower() for s in c.get("skills", [])]
        skill_overlap = [s for s in ans_skills if s in c_skills]
        score += len(skill_overlap) * 8
        if skill_overlap:
            reasons.append(f"{len(skill_overlap)} matching skills")
            
        # Interests match
        ans_interests = [i.lower() for i in answers.get("interests", [])]
        c_interests = [i.lower() for i in c.get("interests", [])]
        interest_overlap = [i for i in ans_interests if i in c_interests]
        score += len(interest_overlap) * 10
        if interest_overlap:
            reasons.append(f"{len(interest_overlap)} matching interests")
            
        # Personality match
        ans_pers = [p.lower() for p in answers.get("personality", [])]
        c_pers = [p.lower() for p in c.get("personality", [])]
        pers_overlap = [p for p in ans_pers if p in c_pers]
        score += len(pers_overlap) * 7
        
        max_possible = 15 + 10 + len(ans_skills) * 8 + len(ans_interests) * 10 + len(ans_pers) * 7
        match_percent = min(100, round((score / max_possible) * 100)) if max_possible > 0 else 0
        
        if score > 0:
            # Recreate structured response
            scored.append({
                "career": c,
                "score": score,
                "matchPercent": match_percent,
                "reasons": reasons
            })
            
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]

def recommend_careers(answers, limit=10):
    logger.info("Generating algorithmic recommendations (local)")
    return recommend_careers_algo(answers, ALL_CAREERS, limit)
