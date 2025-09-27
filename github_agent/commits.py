import os
import json
import requests
from typing import Dict
from dotenv import load_dotenv
from utils import validate_dates, get_commit_history, get_contributor_stats, get_commits_before_date,get_total_commit_count,get_commits_after_date

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY")

if not GITHUB_TOKEN:
    print(
        "Warning: GITHUB_TOKEN not found in environment. API rate limits will be restricted."
    )
if not ASI_ONE_API_KEY:
    print("Warning: ASI_ONE_API_KEY not found in environment.")


class HackathonAnalyzer:
    def __init__(self, hackathon_start: str = None, hackathon_end: str = None):
        self.hackathon_start, self.hackathon_end = validate_dates(
            hackathon_start, hackathon_end
        )

        self.github_headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {GITHUB_TOKEN}" if GITHUB_TOKEN else None,
        }
        self.github_headers = {
            k: v for k, v in self.github_headers.items() if v is not None
        }

        self.LLM_SYSTEM_PROMPT = """
You are an expert Decentralized Audit Analyst for a hackathon integrity platform (HackAudit). Your task is to analyze the provided GitHub repository data and assess its development patterns during the hackathon period using specific weighted heuristics.

**CRITICAL FIRST STEP:**
Before any analysis, you MUST first check if there are any commits within the hackathon period by looking at the dates in line_changes_map. Compare these dates with the hackathon_period.start and hackathon_period.end.

**IMPORTANT NOTICE:**
If there are NO commits with dates between hackathon_period.start and hackathon_period.end:
1. Set trust_score to 0.0
2. Set risk_level to "High"
3. Start the verdict_summary with: "NO COMMITS FOUND DURING THE HACKATHON PERIOD (from [start_date] to [end_date])."
4. Make the first key_anomaly: "No development activity during the hackathon period"
5. You may analyze commits outside the hackathon period, but clearly label them as pre-hackathon activity

**RULES FOR CHEATING DETECTION (Weighted Heuristics):**
1.  **HIGH RISK (Pre-Existing Work/Vendor Dump - 40% Weight):**
    * "Massive Initial Commit": Look for the first 1-2 commits having additions > 5,000 lines or > 100 files changed.
    * "Final Commit Dump": Look for a commit with additions > 3,000 lines occurring minutes before/after the deadline, especially after long inactivity.
    * Lack of Development Flow: Is the history erratic (long gaps followed by large code dumps)?

2.  **MEDIUM RISK (Pacing and Collaboration Anomalies - 35% Weight):**
    * Contributor Imbalance: Does the top contributor account for > 90% of all changes (by additions)?
    * Time Anomaly/Burnout: Are substantial commits clustered at unusual hours?
    * Code Diffusion: Do commits focus heavily on core logic while ignoring config, tests, or documentation?

3.  **LOW RISK (Code Quality/Template Use - 25% Weight):**
    * Negative Churn: Large initial commits with high deletions (> 1,000 lines deleted with few additions).

Please provide your analysis in the following JSON format:

{
    "graph_data": {
        "line_changes_map": [
            {"date": "YYYY-MM-DDTHH:MM:SSZ", "additions": N, "deletions": M, "total": T}
        ],
        "contributor_map": [
            {"user": "username", "commits": N, "additions": M, "deletions": D, "percentage": P}
        ]
        "metadata" : {
            "commits_before": "commits_before","commits_all":"commits_all","commits_after":"commits_after"
        }
    },
    "authenticity_summary": {
        "trust_score": 0.0-1.0,
        "risk_level": "High|Medium|Low",
        "verdict_summary": "Detailed explanation of findings",
        "key_anomalies": ["List of suspicious patterns or concerns"]
    }
}

Focus on providing clear, actionable insights about the project's development during the hackathon period.
"""

    def analyze_repository(self, repo_url: str) -> Dict:
        """Analyze a GitHub repository for hackathon submission."""
        try:
            # Extract owner and repo from URL
            parts = repo_url.rstrip("/").split("/")
            owner = parts[-2]
            repo = parts[-1]

            # Collect repository data
            commits = get_commit_history(
                owner,
                repo,
                self.hackathon_start,
                self.hackathon_end,
                self.github_headers,
            )
            contributors = get_contributor_stats(owner, repo, self.github_headers)

            # Prepare data for LLM analysis
            project_data = {
                "repository": {"owner": owner, "name": repo, "url": repo_url},
                "hackathon_period": {
                    "start": self.hackathon_start.isoformat(),
                    "end": self.hackathon_end.isoformat(),
                },
                "commit_history": commits,
                "contributor_stats": contributors,
                "graph_data": {
                    "line_changes_map": [
                        {
                            "date": commit["date"],
                            "additions": commit["changes"]["additions"],
                            "deletions": commit["changes"]["deletions"],
                            "total": commit["changes"]["total"],
                        }
                        for commit in commits
                    ],
                    "contributor_map": contributors,
                    "metadata": {
                        "commits_before": get_commits_before_date(owner,repo,self.hackathon_start,self.github_headers),
                        "commits_all": get_total_commit_count(owner,repo,self.github_headers),
                        "commits_after": get_commits_after_date(owner,repo,self.hackathon_end,self.github_headers)
                    }
                }
            }

            print(project_data)
            # Call LLM for analysis
            return self.call_llm_for_analysis(project_data)

        except Exception as e:
            return {"error": str(e)}

    def call_llm_for_analysis(self, project_data: Dict) -> Dict:
        """Call ASI.AI API for project analysis."""
        try:
            url = "https://api.asi1.ai/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ASI_ONE_API_KEY}",
            }

            messages = [
                {"role": "system", "content": self.LLM_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(project_data, indent=2)},
            ]

            data = {"model": "asi1-mini", "messages": messages}

            response = requests.post(url, headers=headers, json=data)
            if response.status_code != 200:
                raise Exception(f"ASI.AI API error: {response.status_code}")

            result = response.json()
            print('\nAPI Response:', json.dumps(result, indent=2))
            
            if not result.get('choices') or not result['choices'][0].get('message'):
                raise Exception('Invalid API response format')
                
            content = result['choices'][0]['message']['content']
            print('\nLLM Output:', content)
            
            try:
                # First try to parse it as a direct JSON
                analysis = json.loads(content)
                
                # Verify it has the required structure
                if not isinstance(analysis, dict) or 'graph_data' not in analysis or 'authenticity_summary' not in analysis:
                    raise json.JSONDecodeError('Invalid response structure', content, 0)
                    
                return analysis
            except json.JSONDecodeError as e:
                # If the content contains markdown code block, try to extract JSON from it
                if '```json' in content:
                    try:
                        json_part = content.split('```json')[1].split('```')[0].strip()
                        analysis = json.loads(json_part)
                        
                        # Verify it has the required structure
                        if not isinstance(analysis, dict) or 'graph_data' not in analysis or 'authenticity_summary' not in analysis:
                            raise json.JSONDecodeError('Invalid response structure', json_part, 0)
                            
                        return analysis
                    except (json.JSONDecodeError, IndexError):
                        pass
                        
                # If all parsing attempts fail, create a structured response
                return {
                    'graph_data': {
                        'line_changes_map': project_data.get('graph_data', {}).get('line_changes_map', []),
                        'contributor_map': project_data.get('contributor_stats', []),
                        'metadata':{"commits_before":0,"commits_all":0}
                    },
                    'authenticity_summary': {
                        'trust_score': 0.1,
                        'risk_level': 'High',
                        'verdict_summary': 'Failed to parse LLM response into valid JSON format',
                        'key_anomalies': ['LLM response was not in valid JSON format']
                    }
                }

        except Exception as e:
            return {
                "error": f"LLM analysis failed: {str(e)}",
                "raw_project_data": project_data,
            }


if __name__ == "__main__":
    # Example hackathon dates (ETHDelhi)
    # Note: All times are in UTC
    hackathon_start = "2025-01-25T00:00:00Z"  # Start date (UTC)
    hackathon_end = "2025-09-27T23:59:59Z"  # End date (UTC)

    target_repo_url = "https://github.com/fetchai/asi-alliance-wallet"
    analyzer = HackathonAnalyzer(
        hackathon_start=hackathon_start, hackathon_end=hackathon_end
    )

    print("\nRunning Analysis...")
    report = analyzer.analyze_repository(target_repo_url)

    if "error" in report:
        print(f"Error: {report['error']}")
    else:
        report_file = "report.json"

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nAnalysis complete! Report saved to {report_file}")
        print("\nSummary:")
        print(f"Trust Score: {report['authenticity_summary']['trust_score']}")
        print(f"Risk Level: {report['authenticity_summary']['risk_level']}")
        print("\nVerdict:")
        print(report["authenticity_summary"]["verdict_summary"])
