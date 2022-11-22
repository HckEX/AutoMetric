from fileinput import close
import platform
import os
import sys
from sys import stderr
from textwrap import indent
import urllib
from urllib import response, parse
import requests
import json
from git import Repo
from github import Github
import gitlab
import shutil
from datetime import datetime, timedelta

# hmark clone 후, generate_cli 함수를 import합니다.
try: 
    Repo.clone_from('https://github.com/iotcube/hmark.git','hmark-master')
except:
    print('hmark already exists')


#운영체제에 맞게 hmark 경로 추가 후 hmark 구동에 필요한 ctags.exe를 현재 경로로 복사합니다.
if platform.system() == 'Windows':
    sys.path.append("hmark-master/hmark-4.x/Windows")
    shutil.copy2("hmark-master/hmark-4.x/Windows/ctags.exe", "ctags.exe")

if platform.system() == 'Darwin':
    sys.path.append("hmark-master/hmark-4.x/OSX")
    shutil.copy2("hmark-master/hmark-4.x/OSX/ctags", "ctags")
    os.chmod('ctags', 0o777)

if platform.system() == 'Linux':
    sys.path.append("hmark-master/hmark-4.x/Linux")
    shutil.copy2("hmark-master/hmark-4.x/Linux/ctags", "ctags")
    os.chmod('ctags', 0o777)
    
from hmark import generate_cli


f = open('input.txt')

output = []

while True:
    line = f.readline().strip()
    if not line: break

    # 프로젝트명과 주소에 대한 변수 설정
    prj_repo = line
    query = parse.urlparse(prj_repo)[2][1:]
    domain = parse.urlparse(prj_repo)[1]
    prj_org = query.split('/')[-2]
    prj_name = query.split('/')[-1]


    # print(parse_test[2][1:-4])
    parse_url = parse.quote(prj_repo, safe='')
    # print(parse_url)

    # prj_name = 'libwebsockets'
    # prj_repo = 'https://github.com/warmcat/libwebsockets.git'


    # 오픈소스 리포지토리를 git-clone 폴더에 clone합니다. 
    try: 
        Repo.clone_from(prj_repo,'git-clone/' + prj_name)
    except:
        print('git clone already exists')


    #m1, m2 계산
    try:
        #다운로드 받은 프로젝트의 hidx 파일 생성
        if not os.path.isfile('hidx/hashmark_4_' + prj_name + '.hidx'):
            generate_cli('git-clone/' + prj_name,'on')

        # iotcube API에 생성된 hidx 파일을 전송합니다.
        files = { 'file' : ("hidx/hashmark_4_" + prj_name + ".hidx", open("hidx/hashmark_4_" + prj_name + ".hidx", 'rb'))}
        headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 Edg/106.0.1370.34'}
        response = requests.post("https://iotcube.net/api/wf1", files=files, headers=headers)

        data = json.loads(response.text)

        # m1 - 취약점 수
        m1 = data[0]['total_cve']

        # m1이 0이면 m2도 0으로 계산
        if m1 == 0 :
            m2 = 0
        else :
            # cvss 값을 리스트에 삽입
            cvssList= []
            for cve in data[1:]:
                cvssList.append(cve['cvss'])

            cvssList = list(map(float, cvssList))
            # m2 - 취약점 심각도
            m2 = sum(cvssList) / len(cvssList)

        # print(m2)
    except:
        m1 = 'n/a'
        m2 = 'n/a'

    if domain == 'github.com':
        #github API 토큰 입력
        g = Github('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')

        repo = g.get_repo(query)

        # github 리포지토리의 Contributor list
        contributors = repo.get_contributors()

        now = datetime.now()

        # github 리포지토리의 Release list
        releases = repo.get_releases()
        if releases.totalCount == 0:
            mttu = 'n/a'
        else:
            last_release_page_number = releases.totalCount // 30
            last_release_page = releases.get_page(last_release_page_number)
            first_release = last_release_page[-1]
            first_release_to_now = now - first_release.created_at
            mttu = first_release_to_now.days / releases.totalCount    
        print(mttu)

        # Calculate MTTC
        commits = repo.get_commits()
        last_commit_page_number = commits.totalCount // 30
        last_commit_page = commits.get_page(last_commit_page_number)
        first_commit = last_commit_page[-1]
        first_commit_to_now = now - first_commit.commit.author.date
        mttc = first_commit_to_now.days / commits.totalCount
        print(mttc)

        # Contributor의 수 출력
        m5 = contributors.totalCount
        # print(m5)

        # master branch의 protection 여부 확인
        default_branch = g.get_repo(query).default_branch
        branch = g.get_repo(query).get_branch(default_branch)
        m10 = branch.protected
        # print(m10)

        # 마지막 commit의 날짜 확인
        commit = branch.commit
        latestCommit = commit.commit.author.date
        howLong = now - latestCommit
        m6 = howLong.days
        # print(m6)

    elif domain == 'salsa.debian.org' or domain == 'gitlab.freedesktop.org':
        # GitLab 저장소 불러오기
        salsa = gitlab.Gitlab('https://' + domain)

        project = salsa.projects.get(query)

        branches = project.branches.list()
        for branch in branches:
            jsonbranch = json.loads(branch.to_json())
            if jsonbranch['default'] == True:
                default_branch = jsonbranch
        #print(branch.get_id('protected')
        
        contributors = project.repository_contributors(get_all=True)

        m5 = len(contributors)

        m10 = default_branch['protected']

        # 마지막 commit의 날짜 확인
        now = datetime.now()
        commit_info = default_branch['commit']
        latestCommit = datetime.strptime(commit_info['authored_date'], '%Y-%m-%dT%H:%M:%S.%f%z').replace(tzinfo=None)
        howLong = now - latestCommit
        m6 = howLong.days

    # print('m1` (취약점 수): '+ str(m1))
    # print('m2` (취약점 심각도): '+ str(m2))
    # print('m3 (보안 패치 평균 시간):'+ str(m3))
    # print('m4 (패치되지 않은 취약점): not updated yet')
    # print('m5 (Contributor 수):'+ str(m5))
    # print('m6 (활성도(마지막 Commit으로부터 지난 시간)):'+ str(m6))
    # print('m8 (Dependency SW 평균 업데이트 시간):'+ str(m8))
    # print('m10 (브랜치 보호 기술 적용 여부):'+ str(m10))

    output.append({'name': prj_name, 'Number of CVEs`': str(m1), 'Severity`': str(m2), 'Number of Contributors': str(m5), 'Last Commit Time': str(m6), 'MTTU': str(mttu), 'MTTC': str(mttc),})

f.close()

# JSON 형식으로 결과 출력
outputFile = open('output.json', 'w')
outputFile.write(json.dumps(output, indent=4))
outputFile.close()