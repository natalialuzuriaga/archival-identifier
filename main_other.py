import os
import sys
from datetime import datetime, timedelta
from github import Github

from src.analyzers.issues import GitHubIssuesAnalyzer
from src.analyzers.pull_requests import GitHubPRsAnalyzer
from src.analyzers.releases import GitHubReleasesAnalyzer
from src.analyzers.commit import GitHubCommitsAnalyzer


def generate_markdown_table(stats_list):
    """
    Generate a markdown table from issue statistics.
    
    Args:
        stats_list (list): List of statistics dictionaries from GitHubIssuesAnalyzer
        
    Returns:
        str: Markdown formatted table
    """
    markdown = "# GitHub Issues Report\n\n"
    markdown += "| Repository | Open Issues | Closed Issues | Open PRs | Closed PRs | Releases | Commits |\n"
    markdown += "|---|---|---|---|---|---|---|\n"
    
    for repo, stats in stats_list.items():
        markdown += f"| {repo} | {stats['issues_open_count']} | {stats['issues_closed_count']} | {stats['pr_open_count']} | {stats['pr_closed_count']} | {stats['release_count']} | {stats['commit_count']} |\n"
    
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


def main():
    token = os.environ.get('GITHUB_TOKEN')
    org = os.environ.get('ORG')
    # threshold_days = os.environ.get('THRESHOLD_DAYS')

    g = Github(token)
    organization = g.get_organization(org)

    for repo in organization.get_repos():  # returns a PaginatedList

        # Get repositories in an org
        repository= org + "/" + repo.name

        stats= {}

        print( f"Analyzing repository: {repository}...")  # Debug statement

        # Analyze issues for the repository
        issue_analyzer = GitHubIssuesAnalyzer(repository, 180)
        stats[repository] = issue_analyzer.get_issue_statistics()

        ## Analyze PRs for the repository
        pr_analyzer = GitHubPRsAnalyzer(repository, 180)
        stats[repository].update(pr_analyzer.get_pr_statistics())

        ## Analyze releases for the repository
        release_analyzer = GitHubReleasesAnalyzer(repository, 180)
        stats[repository].update(release_analyzer.get_release_statistics())

        ## Analyze commits for the repository
        commit_analyzer = GitHubCommitsAnalyzer(repository, 180)
        stats[repository].update(commit_analyzer.get_commit_statistics())

        print('Completed analysis for repository: ', repository)  # Debug statement

    # Generate and write markdown file
    markdown_content = generate_markdown_table(stats)
    write_markdown_file(markdown_content)

if __name__ == "__main__":
    main()