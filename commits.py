import os
import requests
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from collections import defaultdict
import time

from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    print("Warning: GITHUB_TOKEN not found in environment. API rate limits will be restricted.")

class HackathonAnalyzer:
    """
    Analyzes a GitHub repository's commit history against hackathon cheating rules.
    It simulates feeding the comprehensive commit data into an LLM for an authenticity verdict.
    """
    def __init__(self, summary_commit_limit: int = 10, 
                 hackathon_start: str = None,
                 hackathon_end: str = None):
        # Set default dates if not provided
        now = datetime.now(timezone.utc)
        if hackathon_end is None:
            hackathon_end = now.isoformat()
        if hackathon_start is None:
            hackathon_start = (now - timedelta(days=2)).isoformat()
            
        # Convert string dates to UTC datetime objects
        try:
            # Add UTC timezone if not specified
            if 'Z' not in hackathon_start and '+' not in hackathon_start:
                hackathon_start += 'Z'
            if 'Z' not in hackathon_end and '+' not in hackathon_end:
                hackathon_end += 'Z'
                
            self.hackathon_start = datetime.fromisoformat(hackathon_start.replace('Z', '+00:00'))
            self.hackathon_end = datetime.fromisoformat(hackathon_end.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(f"Invalid date format. Please use ISO format (YYYY-MM-DDTHH:MM:SS[Z]). Error: {e}")
            
        if self.hackathon_end < self.hackathon_start:
            raise ValueError("Hackathon end date cannot be before start date")
        self.summary_commit_limit = max(1, min(summary_commit_limit, 100))
        self.github_headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {GITHUB_TOKEN}" if GITHUB_TOKEN else None
        }
        self.github_headers = {k: v for k, v in self.github_headers.items() if v is not None}
        
        self.requests_remaining = 5000 if GITHUB_TOKEN else 60
        self.reset_time = None
        
        self.LLM_SYSTEM_PROMPT = """
You are an expert Decentralized Audit Analyst for a hackathon integrity platform (HackAudit). Your task is to analyze the provided JSON data containing a project's *entire commit history* against standard hackathon anti-cheating rules to determine the likelihood of pre-existing work or rushed development.

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

**REQUIRED OUTPUT FORMAT:**

You must return a single JSON object with the following fields:

1.  `graph_data` (Object): Data structures ready for frontend visualization.
    * `line_changes_map`: Array of objects `[{"date": "YYYY-MM-DDTHH:MM:SSZ", "additions": N, "deletions": M, "total": T}]` representing the commit timeline.
    * `contributor_map`: Array of objects `[{"user": "username", "percentage": X.XX}]` for the user contribution graph.

2.  `authenticity_summary` (Object): The main audit verdict.
    * `trust_score`: FLOAT (0.0 to 1.0, where 1.0 is highly authentic).
    * `risk_level`: STRING ("Low", "Medium", "High" - based on the score).
    * `verdict_summary`: STRING (Single paragraph explaining the overall authenticity. Must reference specific rules/heuristics used for the verdict).
    * `key_anomalies`: ARRAY of STRINGS (List 2-3 specific SHAs or patterns that most strongly support the risk level).
"""

    def get_contributor_stats(self, owner: str, repo: str) -> Dict:
        """Get detailed contributor statistics (used total additions as primary metric for analysis)."""
        url = f"https://api.github.com/repos/{owner}/{repo}/stats/contributors"
        
        # GitHub might respond with 202 while calculating stats
        max_retries = 3
        for attempt in range(max_retries):
            response = requests.get(url, headers=self.github_headers)
            
            if response.status_code == 200:
                break
            elif response.status_code == 202:
                print(f"GitHub is calculating stats (attempt {attempt + 1}/{max_retries})...")
                time.sleep(2)  # Wait before retry
            else:
                print(f"Warning: Failed to fetch contributor stats ({response.status_code}).")
                return {}
        
        if response.status_code != 200:
            print("Warning: GitHub stats calculation timed out.")
            return {}

        stats = response.json()
        contributor_data = {}

        for stat in stats:
            username = stat['author']['login'] if stat.get('author') and 'login' in stat['author'] else 'Unknown'
            total_commits = stat['total']
            weekly_stats = stat['weeks']
            
            contributor_data[username] = {
                "total_commits": total_commits,
                "additions": sum(week['a'] for week in weekly_stats),
                "deletions": sum(week['d'] for week in weekly_stats),
                "weeks_active": len([week for week in weekly_stats if week['c'] > 0])
            }

        return contributor_data

    def analyze_commit_content(self, message: str, file_changes: List[Dict], stats: Dict) -> Dict:
        return {
            "ai_likelihood": 0.0,
            "reasoning": "Commit content analysis placeholder.",
            "flags": [],
            "recommendations": []
        }
        
    def _check_rate_limit(self, response: requests.Response) -> bool:
        """Check and handle GitHub API rate limits."""
        if 'X-RateLimit-Remaining' in response.headers:
            self.requests_remaining = int(response.headers['X-RateLimit-Remaining'])
            reset_time = int(response.headers['X-RateLimit-Reset'])
            self.reset_time = datetime.fromtimestamp(reset_time)
            
            if self.requests_remaining < 1:
                wait_time = (self.reset_time - datetime.now()).total_seconds()
                if wait_time > 0:
                    print(f"\nRate limit exceeded. Waiting {int(wait_time)} seconds for reset...")
                    time.sleep(min(wait_time + 1, 3600))  # Wait max 1 hour
                return False
        return True

    def analyze_repository(self, repo_url: str) -> Dict:
        """Analyze a GitHub repository for hackathon submission."""
        parts = repo_url.rstrip('/').split('/')
        owner = parts[-2]
        repo = parts[-1].replace('.git', '')
        
        print(f"\nAnalyzing repository: {owner}/{repo}")

        commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        commits_response = requests.get(commits_url, headers=self.github_headers, params={"per_page": 100})
        
        if not self._check_rate_limit(commits_response):
            return {"error": "Rate limit exceeded. Try again later."}
            
        if commits_response.status_code != 200:
            return {"error": f"Failed to fetch commits. Status: {commits_response.status_code}"}

        commits = commits_response.json()
        
        contributor_stats = self.get_contributor_stats(owner, repo)
        
        commit_analyses = []
        line_changes_map = []
        
        for i, commit in enumerate(commits):
            sha = commit['sha']
            
            commit_detail_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
            
            if self.requests_remaining < 10:  # Ensure we have enough requests left
                self._check_rate_limit(commits_response)
                
            detail_response = requests.get(commit_detail_url, headers=self.github_headers)
            
            if not self._check_rate_limit(detail_response):
                print(f"Warning: Rate limit reached during commit {sha[:7]}. Waiting...")
                continue
                
            if detail_response.status_code != 200:
                print(f"Warning: Failed to fetch detail for {sha[:7]}. Status: {detail_response.status_code}")
                continue
                
            detail = detail_response.json()
            stats = detail.get('stats', {})
            files = detail.get('files', [])

            file_changes = [{
                "file": f['filename'],
                "changes": {
                    "additions": f.get('additions', 0),
                    "deletions": f.get('deletions', 0),
                    "total": f.get('changes', 0)
                }
            } for f in files]
            
            content_analysis = self.analyze_commit_content(
                commit['commit']['message'],
                file_changes,
                stats
            )
            
            commit_data = {
                "sha": sha,
                "date": commit['commit']['author']['date'],
                "author": commit['commit']['author']['name'] if commit['commit']['author'] else 'Unknown',
                "message": commit['commit']['message'].split('\n')[0].strip(),
                "changes": {
                    "files_changed": len(files),
                    "additions": stats.get('additions', 0),
                    "deletions": stats.get('deletions', 0),
                    "total": stats.get('total', 0),
                    "files": [{
                        "name": f['file'],
                        "additions": f['changes']['additions'],
                        "deletions": f['changes']['deletions'],
                        "total": f['changes']['total']
                    } for f in file_changes]
                },
                "content_analysis": content_analysis,
                "index": i 
            }
            commit_analyses.append(commit_data)
            
            line_changes_map.append({
                "date": commit_data['date'],
                "additions": commit_data['changes']['additions'],
                "deletions": commit_data['changes']['deletions'],
                "total": commit_data['changes']['total']
            })
            

        total_additions = sum(stats['additions'] for stats in contributor_stats.values())
        
        contribution_percentages = []
        for username, stats in contributor_stats.items():
            percent_contributed = (stats['additions'] / total_additions * 100) if total_additions > 0 else 0
            contribution_percentages.append({
                "user": username,
                "percentage": round(percent_contributed, 2)
            })
        
        contribution_percentages.sort(key=lambda x: x['percentage'], reverse=True)


        # Process commits for timeline visualization
        timeline_data = [{
            "date": commit['date'],
            "additions": commit['changes']['additions'],
            "deletions": commit['changes']['deletions'],
            "total": commit['changes']['additions'] + commit['changes']['deletions']
        } for commit in commit_analyses]
        
        # Sort timeline by date
        timeline_data.sort(key=lambda x: x['date'])
        
        # Check for commits outside hackathon period
        commits_before_hackathon = []
        commits_after_hackathon = []
        commits_during_hackathon = []
        
        for commit in commit_analyses:
            # Ensure commit date is timezone-aware UTC
            commit_date = datetime.fromisoformat(commit['date'].replace('Z', '+00:00')).astimezone(timezone.utc)
            if commit_date < self.hackathon_start:
                commits_before_hackathon.append(commit)
            elif commit_date > self.hackathon_end:
                commits_after_hackathon.append(commit)
            else:
                commits_during_hackathon.append(commit)
        
        # Calculate risk factors
        first_commit = commits_during_hackathon[-1] if commits_during_hackathon else None
        massive_initial = first_commit and first_commit['changes']['additions'] > 5000
        top_contributor = contribution_percentages[0] if contribution_percentages else {"percentage": 0}
        contributor_imbalance = top_contributor["percentage"] > 90
        
        # Check for suspicious timing
        has_commits_outside_period = bool(commits_before_hackathon or commits_after_hackathon)
        
        # Calculate trust score
        trust_score = 1.0
        anomalies = []
        
        if commits_before_hackathon:
            trust_score -= 0.5
            anomalies.append(f"Found {len(commits_before_hackathon)} commits before hackathon start date ({self.hackathon_start.isoformat()}). Earliest: {commits_before_hackathon[0]['sha'][:7]}")
        
        if commits_after_hackathon:
            trust_score -= 0.3
            anomalies.append(f"Found {len(commits_after_hackathon)} commits after hackathon end date ({self.hackathon_end.isoformat()}). Latest: {commits_after_hackathon[-1]['sha'][:7]}")
        
        if massive_initial:
            trust_score -= 0.4
            anomalies.append(f"Massive initial commit ({first_commit['sha'][:7]}) with {first_commit['changes']['additions']} additions")
        
        if contributor_imbalance:
            trust_score -= 0.3
            anomalies.append(f"Single contributor ({top_contributor['user']}) dominates with {top_contributor['percentage']}% of changes")
        
        # Determine risk level
        risk_level = "High" if trust_score < 0.4 else "Medium" if trust_score < 0.7 else "Low"
        
        # Generate verdict
        verdict = f"Analysis of {len(commit_analyses)} commits shows "
        if risk_level == "High":
            verdict += f"significant red flags. The repository exhibits {', '.join(anomalies).lower()}."
        elif risk_level == "Medium":
            verdict += f"some concerns. {', '.join(anomalies)}."
        else:
            verdict += "organic development patterns with balanced contributions and reasonable commit sizes."
        
        analysis_result = {
            "repository": {
                "owner": owner,
                "name": repo,
                "url": repo_url
            },
            "analysis_date": datetime.now().isoformat(),
            "graph_data": {
                "line_changes_map": timeline_data,
                "contributor_map": contribution_percentages
            },
            "authenticity_summary": {
                "trust_score": round(trust_score, 2),
                "risk_level": risk_level,
                "verdict_summary": verdict,
                "key_anomalies": anomalies
            },
            "metadata": {
                "total_commits": len(commit_analyses),
                "analyzed_commits": min(len(commit_analyses), self.summary_commit_limit),
                "total_contributors": len(contribution_percentages),
                "hackathon_period": {
                    "start": self.hackathon_start.isoformat(),
                    "end": self.hackathon_end.isoformat()
                },
                "commit_timing": {
                    "before_hackathon": len(commits_before_hackathon),
                    "during_hackathon": len(commits_during_hackathon),
                    "after_hackathon": len(commits_after_hackathon)
                },
                "first_commit": commits_before_hackathon[0]['date'] if commits_before_hackathon else 
                               commits_during_hackathon[0]['date'] if commits_during_hackathon else None,
                "last_commit": commits_after_hackathon[-1]['date'] if commits_after_hackathon else
                              commits_during_hackathon[-1]['date'] if commits_during_hackathon else None
            }
        }

        if len(commit_analyses) > 0:
            first_commit = commit_analyses[-1]
            if first_commit['changes']['additions'] > 5000:
                analysis_result['authenticity_summary']['trust_score'] = 0.3
                analysis_result['authenticity_summary']['risk_level'] = "High"
                analysis_result['authenticity_summary']['verdict_summary'] = f"First commit ({first_commit['sha'][:7]}) shows massive code dump of {first_commit['changes']['additions']} lines."
                analysis_result['authenticity_summary']['key_anomalies'].append("Massive initial commit detected")
        
        return analysis_result


    def call_llm_for_analysis(self, full_project_json_data: Dict) -> Dict:
        """
        Executes the LLM analysis with the full project data.
        """
        
        full_project_json_str = json.dumps(full_project_json_data, indent=2)
        
        commits = full_project_json_data['commit_history']
        contributors = full_project_json_data['contributor_stats']

        initial_commit_additions = commits[-1]['changes']['additions'] if commits else 0
        is_massive_initial_dump = initial_commit_additions > 5000 
        
        top_contributor_percent = contributors[0]['percentage'] if contributors else 0
        is_contributor_imbalance = top_contributor_percent > 90
        
        trust_score = 0.95
        anomalies = []
        
        if is_massive_initial_dump:
            trust_score -= 0.4
            anomalies.append(f"Initial commit ({commits[-1]['sha'][:7]}) added {initial_commit_additions} lines. HIGH RISK: Massive code dump.")
        if is_contributor_imbalance:
            trust_score -= 0.2
            anomalies.append(f"Top contributor ({contributors[0]['user']}) accounts for {top_contributor_percent}% of additions. MEDIUM RISK: Collaboration imbalance.")

        trust_score = max(0.1, min(1.0, trust_score))
        
        if trust_score < 0.4:
            risk_level = "High"
        elif trust_score < 0.7:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        if risk_level == "High":
            verdict = f"HIGH RISK: The project exhibits strong signs of pre-existing work. The first commit, {commits[-1]['sha'][:7]}, introduced {initial_commit_additions} lines of code, which is characteristic of a massive initial dump, violating the core principle of organic hackathon development. Further manual review is required."
        elif risk_level == "Medium":
            verdict = f"MEDIUM RISK: While development appears mostly organic, the concentration of effort by one user ({contributors[0]['user']}) with {top_contributor_percent}% of additions is concerning. This suggests a lack of collaborative work (Medium Risk), though no massive initial dumps were detected."
        else:
            verdict = f"LOW RISK: The project shows strong evidence of organic development, featuring small, incremental commits throughout the history. There is no evidence of sudden, massive code dumps that would suggest pre-existing work."
        
        return {
            "graph_data": {
                "line_changes_map": full_project_json_data['graph_timeline_data'],
                "contributor_map": full_project_json_data['contributor_stats']
            },
            "authenticity_summary": {
                "trust_score": round(trust_score, 2),
                "risk_level": risk_level,
                "verdict_summary": verdict,
                "key_anomalies": anomalies or ["No major anomalies detected based on initial heuristics."]
            }
        }

if __name__ == '__main__':
    # Example hackathon dates (ETHDelhi)
    # Note: All times are in UTC
    hackathon_start = "2025-09-25T00:00:00Z"  # Start date (UTC)
    hackathon_end = "2025-09-27T23:59:59Z"    # End date (UTC)
    
    target_repo_url = "https://github.com/fetchai/asi-alliance-wallet"
    analyzer = HackathonAnalyzer(
        summary_commit_limit=10,
        hackathon_start=hackathon_start,
        hackathon_end=hackathon_end
    )
    
    print("\nRunning HackAudit Analysis...")
    report = analyzer.analyze_repository(target_repo_url)
    
    if 'error' in report:
        print(f"Error: {report['error']}")
    else:
        report_file = 'hackaudit_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
