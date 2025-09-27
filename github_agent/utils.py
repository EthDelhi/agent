import os
import requests
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
import time

def validate_dates(hackathon_start: str = None, hackathon_end: str = None) -> tuple[datetime, datetime]:
    """Validate and convert hackathon dates to UTC datetime objects."""
    now = datetime.now(timezone.utc)
    if hackathon_end is None:
        hackathon_end = now.isoformat()
    if hackathon_start is None:
        hackathon_start = (now - timedelta(days=2)).isoformat()
        
    try:
        if 'Z' not in hackathon_start and '+' not in hackathon_start:
            hackathon_start += 'Z'
        if 'Z' not in hackathon_end and '+' not in hackathon_end:
            hackathon_end += 'Z'
            
        start = datetime.fromisoformat(hackathon_start.replace('Z', '+00:00'))
        end = datetime.fromisoformat(hackathon_end.replace('Z', '+00:00'))
        
        if end < start:
            raise ValueError("Hackathon end date cannot be before start date")
            
        return start, end
    except ValueError as e:
        raise ValueError(f"Invalid date format. Please use ISO format (YYYY-MM-DDTHH:MM:SS[Z]). Error: {e}")

def check_rate_limit(response: requests.Response) -> None:
    """Check and handle GitHub API rate limits."""
    if 'X-RateLimit-Remaining' in response.headers:
        requests_remaining = int(response.headers['X-RateLimit-Remaining'])
        reset_timestamp = int(response.headers['X-RateLimit-Reset'])
        reset_time = datetime.fromtimestamp(reset_timestamp, timezone.utc)
        
        if requests_remaining < 5:
            wait_time = (reset_time - datetime.now(timezone.utc)).total_seconds()
            if wait_time > 0:
                print(f"Rate limit low. Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time + 1)

def get_commit_history(owner: str, repo: str, start_date: datetime, end_date: datetime, github_headers: Dict) -> List[Dict]:
    """Fetch detailed commit history including changes and author information. Limited to last 20 commits."""
    commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params = {
        'since': start_date.isoformat(),
        'until': end_date.isoformat(),
        'per_page': 20  # Limit to 20 commits per page
    }
    
    all_commits = []
    page = 1
    
    while True:
        params['page'] = page
        response = requests.get(commits_url, headers=github_headers, params=params)
        check_rate_limit(response)
        
        if response.status_code == 404:
            raise ValueError(f"Repository {owner}/{repo} not found")
        elif response.status_code != 200:
            raise Exception(f"GitHub API error: {response.status_code}")
            
        commits_page = response.json()
        if not commits_page:
            break
            
        for commit in commits_page:
            # Get detailed commit info
            commit_url = commit['url']
            commit_response = requests.get(commit_url, headers=github_headers)
            check_rate_limit(commit_response)
            
            if commit_response.status_code == 200:
                detailed_commit = commit_response.json()
                commit_info = {
                    'sha': detailed_commit['sha'],
                    'author': detailed_commit['commit']['author']['name'],
                    'date': detailed_commit['commit']['author']['date'],
                    'message': detailed_commit['commit']['message'],
                    'changes': {
                        'additions': detailed_commit['stats']['additions'],
                        'deletions': detailed_commit['stats']['deletions'],
                        'total': detailed_commit['stats']['total']
                    },
                    'files': [
                        {
                            'filename': f['filename'],
                            'additions': f['additions'],
                            'deletions': f['deletions'],
                            'changes': f['changes']
                        }
                        for f in detailed_commit['files']
                    ]
                }
                all_commits.append(commit_info)
        
        page += 1
        
    return all_commits


def get_commits_before_date(owner: str, repo: str, before_date: datetime, github_headers: Dict) -> List[Dict]:
    """
    Fetch all commits before a given date from a GitHub repository.
    Handles pagination until no more commits are available.
    """
    commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    all_commits = []
    page = 1

    while True:
        params = {
            "until": before_date.isoformat(),
            "per_page": 100,  # max allowed by GitHub
            "page": page
        }

        response = requests.get(commits_url, headers=github_headers, params=params)
        if response.status_code != 200:
            raise Exception(f"GitHub API error: {response.status_code} - {response.text}")

        commits = response.json()
        if not commits:
            break  # no more commits, exit loop

        all_commits.extend(commits)
        page += 1

    return len(all_commits)


def get_total_commit_count(owner: str, repo: str, github_headers: Dict) -> int:
    """
    Count all commits in a GitHub repository.
    """
    commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    total_count = 0
    page = 1

    while True:
        params = {
            "per_page": 100,  # max allowed
            "page": page
        }

        response = requests.get(commits_url, headers=github_headers, params=params)
        if response.status_code != 200:
            raise Exception(f"GitHub API error: {response.status_code} - {response.text}")

        commits = response.json()
        if not commits:
            break

        total_count += len(commits)
        page += 1

    return total_count

def get_commits_after_date(owner: str, repo: str, after_date: datetime, github_headers: Dict) -> List[Dict]:
    """
    Fetch all commits before a given date from a GitHub repository.
    Handles pagination until no more commits are available.
    """
    commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    all_commits = []
    page = 1

    while True:
        params = {
            "since": after_date.isoformat(),
            "per_page": 100,  # max allowed by GitHub
            "page": page
        }

        response = requests.get(commits_url, headers=github_headers, params=params)
        if response.status_code != 200:
            raise Exception(f"GitHub API error: {response.status_code} - {response.text}")

        commits = response.json()
        if not commits:
            break  # no more commits, exit loop

        all_commits.extend(commits)
        page += 1

    return len(all_commits)
def get_contributor_stats(owner: str, repo: str, github_headers: Dict) -> List[Dict]:
    """Get detailed contributor statistics for the last 20 commits."""
    # First get the last 20 commits
    commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params = {'per_page': 20}
    response = requests.get(commits_url, headers=github_headers, params=params)
    check_rate_limit(response)
    
    if response.status_code != 200:
        return []
    
    commits = response.json()
    
    # Get unique authors from these commits
    contributors = {}
    for commit in commits:
        author = commit['commit']['author']['name']
        if author not in contributors:
            contributors[author] = {
                'user': author,
                'commits': 0,
                'additions': 0,
                'deletions': 0,
                'percentage': 0
            }
        
        # Get detailed commit info for stats
        commit_url = commit['url']
        commit_response = requests.get(commit_url, headers=github_headers)
        check_rate_limit(commit_response)
        
        if commit_response.status_code == 200:
            detailed_commit = commit_response.json()
            contributors[author]['commits'] += 1
            contributors[author]['additions'] += detailed_commit['stats']['additions']
            contributors[author]['deletions'] += detailed_commit['stats']['deletions']
    
    # Calculate percentages
    total_additions = sum(c['additions'] for c in contributors.values())
    if total_additions > 0:
        for author in contributors:
            contributors[author]['percentage'] = round(
                (contributors[author]['additions'] / total_additions * 100), 2
            )
    
    # Convert to list and sort by additions
    contributor_list = list(contributors.values())
    return sorted(contributor_list, key=lambda x: x['additions'], reverse=True)

