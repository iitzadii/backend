import os
import json
import logging
import google.generativeai as genai

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

def recommend_careers_gemini(answers, careers, api_key, limit=10):
    try:
        genai.configure(api_key=api_key)
        
        # Prepare careers summary for model context to keep token usage minimal
        careers_summary = []
        for c in careers:
            careers_summary.append({
                "id": c["id"],
                "title": c["title"],
                "category": c["category"],
                "skills": c["skills"],
                "interests": c["interests"],
                "personality": c["personality"],
                "qualifications": c["qualifications"],
                "streams": c["streams"]
            })
            
        prompt = f"""
You are an expert Career Counsellor. Analyze the user's career quiz responses and suggest the best matches from our predefined career catalog.

USER ANSWERS:
- Current Qualification: {answers.get('qualification', 'None')}
- Stream Interests: {answers.get('stream', 'None')}
- User's Skills: {', '.join(answers.get('skills', []))}
- User's Interests: {', '.join(answers.get('interests', []))}
- User's Personality Traits: {', '.join(answers.get('personality', []))}

AVAILABLE PREDEFINED CATALOG:
{json.dumps(careers_summary, indent=2)}

INSTRUCTIONS:
1. Select the top career matches (up to {limit}) from the catalog list ONLY. Do not invent any new career ID.
2. For each recommendation:
   - Provide the EXACT 'id' from the catalog.
   - Calculate a match percentage (integer 1 to 100) indicating how well it fits.
   - Provide 2 or 3 short, personalized, highly engaging sentences as reasons (reason strings in an array) why this career matches their specific answers. Refer to their chosen skills/interests directly in the reasons to make it personalized.
3. Return the results as a JSON list matching the schema exactly.

Example output:
[
  {{
    "id": "software-engineer",
    "matchPercent": 95,
    "reasons": [
      "Your programming skill and logical interests match perfectly with software engineering.",
      "As an analytical personality type, you will enjoy solving complex software problems."
    ]
  }}
]
"""
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        raw_json = response.text.strip()
        data = json.loads(raw_json)
        
        recs = []
        for item in data:
            c_id = item.get("id")
            if c_id in CAREER_MAP:
                recs.append({
                    "career": CAREER_MAP[c_id],
                    "score": item.get("matchPercent", 50), # Use matchPercent as score rank
                    "matchPercent": item.get("matchPercent", 50),
                    "reasons": item.get("reasons", ["Matches your profile"])
                })
        
        # Sort just in case
        recs.sort(key=lambda x: x["matchPercent"], reverse=True)
        return recs[:limit]
        
    except Exception as e:
        logger.error(f"Gemini recommendations failed: {e}. Falling back to algorithm.")
        return recommend_careers_algo(answers, careers, limit)

def recommend_careers(answers, limit=10):
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        logger.info("Generating AI recommendations using Gemini API")
        return recommend_careers_gemini(answers, ALL_CAREERS, api_key, limit)
    else:
        logger.info("Generating algorithmic recommendations (local)")
        return recommend_careers_algo(answers, ALL_CAREERS, limit)
