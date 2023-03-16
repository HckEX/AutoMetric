from urllib import parse
import json
from github import Github
import gitlab
from datetime import datetime

f = open('input.txt')
githubToken = ''

output = []

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

    parse_url = parse.quote(prj_repo, safe='')

    # if repository is GitHub repository
    if domain == 'github.com':
        # set github API token
        g = Github(githubToken)

        print(query)
        gitRepo = g.get_repo(query)

        # get contributor list of repositories
        contributors = gitRepo.get_contributors()

        now = datetime.now()

        # get release list of repositories
        try:
            releases = gitRepo.get_releases()
            if releases.totalCount == 0:
                MU = 'n/a'
            else:
                last_release_page_number = (releases.totalCount - 1) // 30
                last_release_page = releases.get_page(last_release_page_number)
                first_release = last_release_page[-1]
                first_release_to_now = now - first_release.created_at
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
                first_commit_to_now = now - first_commit.commit.author.date
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
            latestCommit = commit.commit.author.date
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
        BP = len(contributors)

        # check BP
        m10 = default_branch['protected']

        # calculate IP
        now = datetime.now()
        commit_info = default_branch['commit']
        latestCommit = datetime.strptime(commit_info['authored_date'], '%Y-%m-%dT%H:%M:%S.%f%z').replace(tzinfo=None)
        howLong = now - latestCommit
        IP = howLong.days

    output.append({'name': prj_name, 'Number of Contributors': str(NC), 'Inactive Period': str(IP), 'MTTU': str(MU), 'MTTC': str(MC), 'Branch Protection': BP})

f.close()

# JSON output
outputFile = open('output.json', 'w')
outputFile.write(json.dumps(output, indent=4))
outputFile.close()
