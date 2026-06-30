import asyncio
from typing import List, Dict, Any
from llm import LLMProvider

class ApplicationMaterialGenerator:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def _build_cv_prompt(self, base_cv: str, accomplishments: List[Dict[str, Any]], job_description: str) -> str:
        feats_text = "\n".join([
            f"- [{f.get('title')}] {f.get('description')} (Tags: {', '.join(f.get('skills_used', []))})"
            for f in accomplishments
        ])
        
        return f"""
You are an expert recruiter and CV writer. I will provide my master CV (in Markdown), a target Job Description, and a list of my accomplishments/feats.
Please rewrite and reorganize my CV to highlight the experience, tech stack, and keywords relevant to this job description.
Use the relevant accomplishments/feats listed below to bolster the project descriptions or work experience on my CV. Do not invent details.

Master CV:
{base_cv}

My Dump of Accomplishments/Feats:
{feats_text}

Job Description:
{job_description}

Provide the tailored CV in clean, valid Markdown formatting only. Do not wrap the output in markdown block codes (like ```markdown ... ```) - just output the raw markdown.
"""

    def _build_cover_letter_prompt(self, base_cv: str, accomplishments: List[Dict[str, Any]], company: str, job_title: str, job_description: str) -> str:
        feats_text = "\n".join([
            f"- [{f.get('title')}] {f.get('description')} (Tags: {', '.join(f.get('skills_used', []))})"
            for f in accomplishments
        ])
        
        return f"""
Write a professional French cover letter (Lettre de Motivation) for the role of '{job_title}' at '{company}' based on my CV and specific accomplishments.
You MUST strictly follow the French standard 'Moi, Vous, Nous' (Me, You, Us) structure:
1. **Moi (Me)**: Hook highlighting my profile, key skills, and select highly-relevant feats from my accomplishments list.
2. **Vous (You)**: Focus on the company, their technical challenges, values, or target market as inferred from the job description.
3. **Nous (Us)**: Detail what we can achieve together, bridging my capabilities and listed accomplishments with their issues, followed by a formal request for an interview.

My CV:
{base_cv}

My Relevant Accomplishments/Feats:
{feats_text}

Job Description:
{job_description}

Tone: Professional, persuasive, written in perfect, formal French (using 'vouvoiement'). Do not use generic placeholders; output a ready-to-copy letter. Do not wrap the output in markdown code blocks - just output the text.
"""

    async def generate(self, base_cv: str, accomplishments: List[Dict[str, Any]], job: Dict[str, Any]) -> Dict[str, str]:
        cv_system = "You are a professional CV optimizer. Output only valid Markdown."
        cl_system = "You are an expert French career coach writing formal Lettres de Motivation."

        cv_prompt = self._build_cv_prompt(base_cv, accomplishments, job.get("description", ""))
        cl_prompt = self._build_cover_letter_prompt(
            base_cv, 
            accomplishments, 
            job.get("company", "l'entreprise"), 
            job.get("title", "Développeur"), 
            job.get("description", "")
        )

        # Run LLM calls concurrently
        tailored_cv, cover_letter = await asyncio.gather(
            self.llm.generate_text(cv_prompt, system_instruction=cv_system),
            self.llm.generate_text(cl_prompt, system_instruction=cl_system)
        )

        return {
            "tailored_cv": tailored_cv.strip(),
            "cover_letter": cover_letter.strip()
        }
