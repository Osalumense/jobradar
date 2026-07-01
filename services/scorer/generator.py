import asyncio
from typing import List, Dict, Any, Optional
from llm import LLMProvider

class ApplicationMaterialGenerator:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def _build_cv_prompt(self, base_cv: str, accomplishments: List[Dict[str, Any]], job_description: str) -> str:
        feats_text = "\n".join([
            f"- [{f.get('title')}] {f.get('description')} (Tags: {', '.join(f.get('skills_used', []))})"
            for f in accomplishments
        ])
        return f"""You are an expert recruiter and CV writer. Rewrite the master CV below to be perfectly tailored for the job description provided.

Rules:
- Reorder and rephrase experience sections to lead with the most relevant skills and achievements.
- Weave in the accomplishments listed below naturally — do not fabricate details.
- Mirror the language and keywords from the job description.
- Keep all factual information accurate; do not invent new roles or projects.
- Output clean Markdown only. No code fences, no commentary.

Master CV:
{base_cv}

Accomplishments to draw from:
{feats_text if feats_text.strip() else '(none provided)'}

Job Description:
{job_description}
"""

    def _build_cover_letter_prompt(self, base_cv: str, accomplishments: List[Dict[str, Any]], company: str, job_title: str, job_description: str) -> str:
        feats_text = "\n".join([
            f"- [{f.get('title')}] {f.get('description')} (Tags: {', '.join(f.get('skills_used', []))})"
            for f in accomplishments
        ])
        return f"""Write a professional cover letter for the role of '{job_title}' at '{company}'.

Strictly follow the French 'Moi, Vous, Nous' structure:
1. **Moi**: Open with a compelling hook about my profile and most relevant accomplishments.
2. **Vous**: Show understanding of the company's challenges and context from the job description.
3. **Nous**: Bridge my skills to their needs and close with a confident interview request.

Tone: professional, persuasive, formal French (vouvoiement). No placeholders. Ready to send.
Output plain text only — no markdown headers, no code fences.

My CV:
{base_cv}

My relevant accomplishments:
{feats_text if feats_text.strip() else '(none provided)'}

Job Description:
{job_description}
"""

    def _build_qa_prompt(self, base_cv: str, accomplishments: List[Dict[str, Any]], job: Dict[str, Any], questions_text: str) -> str:
        feats_text = "\n".join([
            f"- [{f.get('title')}] {f.get('description')} (Tags: {', '.join(f.get('skills_used', []))})"
            for f in accomplishments
        ])
        return f"""You are helping a candidate prepare strong, tailored answers for a job application.

The candidate is applying for: {job.get('title')} at {job.get('company')}

Instructions:
- Identify each distinct question or prompt from the text below.
- Write a tailored answer for each one drawing from the candidate's CV and accomplishments.
- Answers should be concise (2-4 sentences each), specific, and use real details from the CV/accomplishments.
- If a question asks "why us" or "why this company", infer the answer from the job description.
- Format output as:
  **Q: [exact question]**
  A: [tailored answer]
  (blank line between each Q&A pair)

Candidate CV:
{base_cv}

Candidate accomplishments:
{feats_text if feats_text.strip() else '(none provided)'}

Job description:
{job.get('description', '')}

Application questions/prompts to answer:
{questions_text}
"""

    def _build_suggest_feats_prompt(self, feats: List[Dict[str, Any]], job: Dict[str, Any]) -> str:
        feats_list = "\n".join([
            f"{i+1}. [{f.get('id')}] {f.get('title')}: {f.get('description')[:200]} (skills: {', '.join(f.get('skills_used', []))})"
            for i, f in enumerate(feats)
        ])
        return f"""You are helping a candidate select the most relevant accomplishments for a job application.

Job: {job.get('title')} at {job.get('company')}
Description: {job.get('description', '')[:1500]}

Candidate's accomplishments:
{feats_list}

Task: Return a JSON array of objects, one per accomplishment, ordered by relevance (most relevant first).
Each object must have exactly these fields:
- "id": the UUID from the brackets above (e.g. "abc-123")
- "relevant": true if this accomplishment is worth including, false otherwise
- "reason": one short sentence explaining why it is or isn't relevant

Return ONLY the JSON array, no other text.
"""

    async def generate(
        self,
        base_cv: str,
        accomplishments: List[Dict[str, Any]],
        job: Dict[str, Any],
        application_questions: Optional[str] = None
    ) -> Dict[str, str]:
        cv_system = "You are a professional CV optimizer. Output only valid Markdown."
        cl_system = "You are an expert French career coach writing formal Lettres de Motivation."
        qa_system = "You are a job application coach. Write concise, specific, truthful answers."

        cv_prompt = self._build_cv_prompt(base_cv, accomplishments, job.get("description", ""))
        cl_prompt = self._build_cover_letter_prompt(
            base_cv, accomplishments,
            job.get("company", "l'entreprise"),
            job.get("title", "ce poste"),
            job.get("description", "")
        )

        tasks = [
            self.llm.generate_text(cv_prompt, system_instruction=cv_system),
            self.llm.generate_text(cl_prompt, system_instruction=cl_system),
        ]

        qa_task = None
        if application_questions and application_questions.strip():
            qa_prompt = self._build_qa_prompt(base_cv, accomplishments, job, application_questions)
            tasks.append(self.llm.generate_text(qa_prompt, system_instruction=qa_system))

        results = await asyncio.gather(*tasks)

        output = {
            "tailored_cv": results[0].strip(),
            "cover_letter": results[1].strip(),
            "qa_answers": results[2].strip() if len(results) > 2 else None,
        }
        return output

    async def suggest_feats(self, feats: List[Dict[str, Any]], job: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ask Gemini to rank and annotate feats by relevance to this job."""
        import json

        if not feats:
            return []

        prompt = self._build_suggest_feats_prompt(feats, job)
        system = "You are a career advisor. Return only valid JSON arrays, no prose."

        raw = await self.llm.generate_text(prompt, system_instruction=system)

        # Strip markdown code fences if present
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1]
            clean = clean.rsplit("```", 1)[0]

        try:
            suggestions = json.loads(clean)
        except Exception:
            # Fallback: return all feats as relevant with no reason
            suggestions = [{"id": str(f["id"]), "relevant": True, "reason": ""} for f in feats]

        # Merge suggestion metadata back onto the full feat objects
        feat_map = {str(f["id"]): f for f in feats}
        result = []
        for s in suggestions:
            feat = feat_map.get(s.get("id"))
            if feat:
                result.append({
                    **feat,
                    "suggested": s.get("relevant", True),
                    "reason": s.get("reason", ""),
                })
        return result
