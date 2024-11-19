from urllib import parse
import json
from github import Github
import gitlab
from datetime import datetime, timezone
from dateutil import parser
import requests

f = open('input.txt')
githubToken = ''

output = []

# Ensure that 'now' is timezone-aware
now = datetime.now(timezone.utc)

def parse_dates_from_tags(tags, owner, repo, token):
    dates = [] # Initialize the dates list
    api_url = f"https://api.github.com/repos/{owner}/{repo}" # GitHub API base URL
    headers = {"Authorization": f"token {token}"} # Set the Authorization header

    for tag in tags: # Iterate over the tags
        commit_url = f"{api_url}/git/refs/tags/{tag['name']}" # Get the commit URL
        tag_data = requests.get(commit_url, headers=headers).json() # Get the tag data

        if tag_data["object"]["type"] == "tag": # If the tag is annotated
            annotated_tag_url = tag_data["object"]["url"] # Get the annotated tag URL
            annotated_tag_data = requests.get(annotated_tag_url, headers=headers).json() # Get the annotated tag data
            commit_sha = annotated_tag_data["object"]["sha"] # Get the commit SHA
        else: # If the tag is not annotated
            commit_sha = tag_data["object"]["sha"] # Get the commit SHA

        commit_data = requests.get(f"{api_url}/commits/{commit_sha}", headers=headers).json() # Get the commit details

        if "commit" in commit_data and "committer" in commit_data["commit"]: # Check for valid commit data
            commit_date = commit_data["commit"]["committer"]["date"] # Get the commit date
           # Convert commit_date to a timezone-aware datetime
            dates.append(parser.isoparse(commit_date)) # Append the parsed date

    return dates # Return the dates list

def calculate_mttu_from_dates(dates):
    """
    Calculate the Mean Time to Update (MTTU) given a list of datetime objects.
    """
    if len(dates) < 2: # If there are less than 2 dates
        return "n/a" # Return "n/a"

    dates.sort() # Sort dates in ascending order
    time_diffs = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))] # Calculate time differences between successive dates
    mttu = sum(time_diffs) / len(time_diffs) # Calculate average time difference

    return mttu # Return the Mean Time to Update (MTTU)

def get_github_tags(owner, repo, token):
    """
    Fetch the tags from the GitHub repository.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/tags"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(api_url, headers=headers)
    return response.json() if response.status_code == 200 else []

while True:
    line = f.readline().strip()
    if not line: break

    # set name and url of project
    prj_repo = line
    query = parse.urlparse(prj_repo)[2][1:]
    print(query)
    domain = parse.urlparse(prj_repo)[1]
    prj_org = query.split('/')[-2]
    prj_name = query.split('/')[-1]

    # if repository is GitHub repository
    if domain == 'github.com':
        # set github API token
        g = Github(githubToken)

        print(query)
        gitRepo = g.get_repo(query)

        # get release list of repositories
        try:
            releases = gitRepo.get_releases()
            if releases.totalCount == 0:
                tags = get_github_tags(prj_org, prj_name, githubToken)
                if tags:
                    tag_dates = parse_dates_from_tags(tags, prj_org, prj_name, githubToken)
                    MU = calculate_mttu_from_dates(tag_dates) if tag_dates else 'n/a'
                else:
                    MU = 'n/a'
            else:
                last_release_page_number = (releases.totalCount - 1) // 30
                last_release_page = releases.get_page(last_release_page_number)
                first_release = last_release_page[-1]
                first_release_to_now = now - first_release.created_at.replace(tzinfo=timezone.utc)
                MU = first_release_to_now.days / releases.totalCount    
        except:
            MU = 'n/a'   

        # calculate MC
        try:
            commits = gitRepo.get_commits()
            if commits.totalCount == 0:
                MC = 'n/a'
            else:
                last_commit_page_number = (commits.totalCount - 1) // 30
                last_commit_page = commits.get_page(last_commit_page_number)
                first_commit = last_commit_page[-1]
                first_commit_to_now = now - first_commit.commit.author.date.replace(tzinfo=timezone.utc)
                MC = first_commit_to_now.days / commits.totalCount
        except:
            MC = 'n/a'

        # calculate NC
        contributors = gitRepo.get_contributors()
        try:
            NC = contributors.totalCount
            NC +=1
        except:
            NC = 'n/a'

        # check BP
        try:
            default_branch = gitRepo.default_branch
            branch = gitRepo.get_branch(default_branch)
            BP = branch.protected
        except:
            BP = 'n/a'

        # calculate IP
        try:
            commit = branch.commit
            latestCommit = commit.commit.author.date.replace(tzinfo=timezone.utc)
            howLong = now - latestCommit
            IP = howLong.days
        except:
            IP = 'n/a'

    # if repository is gitlab repository
    elif domain == 'salsa.debian.org' or domain == 'gitlab.freedesktop.org':
        # set gitlab repository
        salsa = gitlab.Gitlab('https://' + domain)

        project = salsa.projects.get(query)

        # set branch
        branches = project.branches.list()
        for branch in branches:
            jsonbranch = json.loads(branch.to_json())
            if jsonbranch['default'] == True:
                default_branch = jsonbranch
        
        # calculate NC
        contributors = project.repository_contributors(get_all=True)
        NC = len(contributors)

        # check BP
        m10 = default_branch['protected']

        # calculate IP
        now = datetime.now(timezone.utc)
        commit_info = default_branch['commit']
        latestCommit = datetime.strptime(commit_info['authored_date'], '%Y-%m-%dT%H:%M:%S.%f%z').replace(tzinfo=None)
        latestCommit = latestCommit.replace(tzinfo=timezone.utc)
        howLong = now - latestCommit
        IP = howLong.days

    output.append({'name': prj_name, 'Number of Contributors': str(NC), 'Inactive Period': str(IP), 'MTTU': str(MU), 'MTTC': str(MC), 'Branch Protection': BP})

f.close()

# JSON output
outputFile = open('output.json', 'w')
outputFile.write(json.dumps(output, indent=4))
outputFile.close()
