import httpx
import os
from typing import Dict, Any

class ResendAlerter:
    def __init__(self):
        self.api_key = os.environ.get("RESEND_API_KEY")
        self.to_email = os.environ.get("ALERT_TO_EMAIL")
        
        # Default to onboarding sender address if domain is not configured
        self.from_email = os.environ.get("ALERT_FROM_EMAIL", "JobRadar AI <onboarding@resend.dev>")
        
        if not self.api_key or not self.to_email:
            raise ValueError("RESEND_API_KEY and ALERT_TO_EMAIL must be set in environment variables")
            
        self.api_key = self.api_key.strip('"').strip("'")
        self.to_email = self.to_email.strip('"').strip("'")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.api_url = "https://api.resend.com/emails"

    async def send_job_alert(self, client: httpx.AsyncClient, job: Dict[str, Any], score_details: Dict[str, Any]) -> bool:
        """Send an HTML email alert for a high-matching job posting."""
        score_pct = int(score_details["composite"] * 100)
        stars = "🟢" if score_pct >= 80 else "🟡" if score_pct >= 70 else "🟠"
        
        subject = f"{stars} {score_pct}% Match: {job['title']} at {job['company']}"
        
        html_content = f"""
        <h2>JobRadar AI Matching Alert</h2>
        <p>A new high-scoring job posting has been found:</p>
        <hr/>
        <h3>{job['title']} — {job['company']}</h3>
        <p><b>Match Score:</b> {score_pct}% ({stars})</p>
        <ul>
            <li><b>Contract:</b> {job['contract_type'].upper() if job.get('contract_type') else 'Non spécifié'}</li>
            <li><b>Location:</b> {job['location'] or 'Non précisé'}</li>
            <li><b>Source:</b> {job['source']}</li>
        </ul>
        <p><b>Score Breakdown:</b></p>
        <ul>
            <li>Semantic Score: {int(score_details['semantic']*100)}%</li>
            <li>Keyword Match: {int(score_details['keyword']*100)}%</li>
            <li>Recency Score: {int(score_details['recency']*100)}%</li>
        </ul>
        <p><b>Link:</b> <a href="{job['url']}" target="_blank">View Posting on {job['source'].upper()}</a></p>
        <hr/>
        <p><i>Log in to your JobRadar AI dashboard to tailor your CV and generate your "Moi, Vous, Nous" cover letter!</i></p>
        """
        
        payload = {
            "from": self.from_email,
            "to": [self.to_email],
            "subject": subject,
            "html": html_content
        }
        
        try:
            response = await client.post(self.api_url, headers=self.headers, json=payload)
            if response.status_code in [200, 201]:
                return True
            else:
                print(f"Failed to send email via Resend. Code: {response.status_code}, Body: {response.text}")
                return False
        except Exception as e:
            print(f"Exception raised while sending Resend alert: {e}")
            return False
