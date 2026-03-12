import json
import sys
import subprocess
import os
from datetime import datetime, timedelta
from github import Github

def generate_markdown_table(stats_list):
    """
    Generate a markdown table from issue statistics.
    
    Args:
        stats_list (list): List of statistics dictionaries from GitHubIssuesAnalyzer
        
    Returns:
        str: Markdown formatted table
    """
    markdown = "# GitHub Issues Report\n\n"
    markdown += "| Repository | Open Issues | Closed Issues | Open PRs | Merged PRs | Closed PRs | Releases | Commits | Dependants | Criticality Score | Forks | Active Forks | Status |\n"
    markdown += "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    
    for repo, stats in stats_list.items():
        markdown += f"| {repo} | {stats['issues_open_count']} | {stats['issues_closed_count']} | {stats['pr_open_count']} | {stats['pr_merged_count']} | {stats['pr_closed_count']} | {stats['release_count']} | {stats['commit_count']} | {stats['dependents_count']} | {stats['criticality_score']} | {stats['forks_count']} | {stats['active_forks_count']} | {stats['status']} |\n"
    
    return markdown

def write_markdown_file(markdown_content, output_path="archival_candidates_report.md"):
    """
    Write markdown content to a file.
    
    Args:
        markdown_content (str): The markdown content to write
        output_path (str): Path where the markdown file should be saved
    """
    with open(output_path, 'w') as f:
        f.write(markdown_content)
    print(f"Markdown report written to {output_path}")

def get_criticality_score(org_name, repo_name, api_token):
    """See https://github.com/ossf/criticality_score for more details on the OpenSSF Criticality Score.
    
    org_name (str)
    repo_name (str)
    api_token (str)

    dependents_count (str)
    criticality_score (str): This value ranges from 0 to 1 (like a float) with lower scores indicating less critical projects.
    
    """
    
    os.environ['GITHUB_AUTH_TOKEN'] = api_token

    cmd_str = 'criticality_score --repo github.com/' + org_name + '/' + repo_name + ' --format csv'

    try:
        proc = subprocess.Popen(cmd_str, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        out, err = proc.communicate()
        
        if not err:
            csv_str = out.decode("utf-8")
            items = csv_str.split(',')
            dependents_count = items[25]
            criticality_score = items[26].rstrip()
        else: 
            dependents_count = None
            criticality_score = None
    except:
        dependents_count = None
        criticality_score = None

    return dependents_count, criticality_score

def define_status_determination(stats):
    """
    Determine the status of a repository based on its statistics.
    
    stats (dict): A dictionary containing development activity statistics for a repository
        
    str: The determined status of the repository (e.g., "Active", "Dormant")
    """
    # Placeholder logic for status determination
    if all(stats.get(field, 0) == 0 for field in [
        "issues_open_count",
        "issues_closed_count",
        "pr_open_count",
        "pr_merged_count",
        "pr_closed_count",
        "release_count",
        "commit_count",
        "active_forks_count"
    ]):
        return "Dormant"
    else:
        return "Active"

def analyze_fork_activity(repo):
    """
    Analyze the activity of forks for a given repository.
    
    repo_obj: A PyGithub Repository object
    
    dict: A dictionary containing statistics about the forks (e.g., number of forks, recent activity)
    """

    g = Github(os.getenv("GITHUB_AUTH_TOKEN"))
    org_name = "DSACMS"
    
    cutoff_date = datetime.utcnow() - timedelta(days=180)
    cutoff_date_str = cutoff_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    repo_obj = g.get_repo(f"{org_name}/{repo}")
    forks_count = len(list(repo_obj.get_forks()))
    active_forks = []

    for fork in repo_obj.get_forks():
        print(f"Analyzing fork: {fork.full_name}...")  # Debug statement
        
        # First check for recent activity in fork
        if fork.pushed_at < datetime.now(fork.pushed_at.tzinfo) - timedelta(days=180):
            print(f"{fork.full_name} has no recent activity.")
            continue
        
        # Then check if fork has diverged / has unique commits
        try:
            # Compare the fork's default branch with the parent's default branch
            comparison = repo_obj.compare(repo_obj.default_branch, fork.default_branch)

            if comparison.ahead_by > 0:
                # The fork has unique commits! It's active.
                active_forks.append((fork, comparison.ahead_by))
            else:
                # The fork is not ahead, so it has no new commits on its default branch
                print(f"{fork.full_name} has no unique commits.")
                continue

        except Exception as e:
            # Fork has an empty default branch or encountered other issues. Classify as inactive.
            if e.status == 404:
                print("Error")
            else:
                print(f"\nCould not compare {fork.full_name}: {e}")
    
    return forks_count, len(active_forks)


def main():
    development_activity_file = sys.argv[1]

    with open(development_activity_file, 'r') as f:
        data = json.load(f)

    stats= {}

    for repo in data["repos"]:
        print(f"Analyzing repository's development activity: {repo['name']}...")  # Debug statement

        # Calculate statistics for the repository
        stats[repo["name"]] = {
            "issues_open_count": len([issue for issue in repo["issues"] if issue["state"] == "open"]),
            "issues_closed_count": len([issue for issue in repo["issues"] if issue["state"] == "closed"]),
            # TODO: for pulls, add the author
            # TODO: filter pulls by author and mentions of "code.json" in the title
            "pr_open_count": len([pr for pr in repo["pulls"] if pr["state"] == "open"]),
            "pr_merged_count": len([pr for pr in repo["pulls"] if pr["state"] == "closed" and pr["merged"] == True]),
            "pr_closed_count": len([pr for pr in repo["pulls"] if pr["state"] == "closed" and pr["merged"] == False]),
            "release_count": "N/A",
            "commit_count": len(repo["commits"])
        }

        # Run OpenSSF Criticality Score
        dependents_count, criticality_score = get_criticality_score("DSACMS", repo["name"], os.getenv("GITHUB_AUTH_TOKEN"))
        stats[repo["name"]]["dependents_count"] = dependents_count # dependents_count
        stats[repo["name"]]["criticality_score"] = criticality_score # criticality_score

        # TODO: Analyze fork activity
        forks_count, active_forks_count = analyze_fork_activity(repo["name"])
        stats[repo["name"]]["forks_count"] = forks_count
        stats[repo["name"]]["active_forks_count"] = active_forks_count

        # Determine the status of the repository
        stats[repo["name"]]["status"] = define_status_determination(stats[repo["name"]])

    # print(stats)

    # Generate and write markdown file
    markdown_content = generate_markdown_table(stats)
    write_markdown_file(markdown_content)

if __name__ == "__main__":
    main()