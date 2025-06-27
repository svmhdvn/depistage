# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "aiohttp[speedups]"
# ]
# ///

import aiohttp
import asyncio
import pathlib

# TODO:
# * only works for amd64 now
# * if the same test is failing on multiple archs, file the bug as 'platform = any'

def jenkinsCaseToKyuaFilter(t):
    return f"{t['className'].replace('.', '/')}:{t['name']}"

async def jenkinsLatestTestRun(session):
    url = '/view/Test/job/FreeBSD-main-amd64-test/lastCompletedBuild/testReport/api/json'
    params = {'tree': 'suites[cases[age,className,name,failedSince]]'}
    async with session.get(url, params=params) as resp:
        return (await resp.json())['suites'][0]['cases']

# TODO might need 'comment' field instead of 'msg'
async def jenkinsBuildMetadataKv(session, build_num):
    url = f'/view/Test/job/FreeBSD-main-amd64-test/{build_num}/api/json'
    params = {'tree': 'changeSet[items[commitId,author[id],msg]]'}
    async with session.get(url, params=params) as resp:
        return (build_num, (await resp.json())['changeSet']['items'])

async def fetchJenkinsData(session):
    j = await jenkinsLatestTestRun(session)
    failed_tests = [
        {'name': jenkinsCaseToKyuaFilter(t), 'failedSince': t['failedSince']
        for t in j if t['failedSince'] > 0
    ]
    unique_failed_since = frozenset(t['failedSince'] for t in failed_tests)
    buildnum_to_metadata = dict(await asyncio.gather(*(jenkinsBuildMetadataKv(session, bn) for bn in unique_failed_since)))
    return {'failed_tests': failed_tests, 'past_builds': buildnum_to_metadata}

async def bugzillaSearchExistingBugs(session, api_key):
    url = '/bugzilla/rest/bug'
    params = {'api_key': api_key,'keywords': 'ci'}
    async with session.get(url, params=params) as resp:
        return (await resp.json())['bugs']

async def fetchBugzillaData(session, api_key):
    existing_bugs = await bugzillaSearchExistingBugs(session, api_key)
    return {'existing_bugs': existing_bugs}

async def bugzillaReopenClosedBug(session):
    pass

async def bugzillaFileNewBug(session):
    pass

async def main():
    api_key = pathlib.Path('/home/siva/src/playground/bugstest_apikey.txt').read_text()

    # TODO change to production bugzilla URL once ready
    async with
        aiohttp.ClientSession('https://ci.freebsd.org') as jenkins_session,
        aiohttp.ClientSession('https://bugstest.freebsd.org') as bugzilla_session:

        jenkins_data, bugzilla_data = await asyncio.gather(
            fetchJenkinsData(jenkins_session),
            fetchBugzillaData(bugzilla_session, api_key),
        )

        # convert Jenkins-style test names to Kyua-style test filters
        failing_case_names = [t['name'] for t in jenkins_data['failed_tests']]
        print(failing_case_names)
        print()

        for t in jenkins_data['failed_tests']:
            test_found = False
            for b in bugzilla_data['existing_bugs']:
                if t['name'] not in b['summary']: continue

                test_found = True
                # already being tracked, no-op
                if b['status'] != 'Closed': continue

                # TODO reopen the previous bug to preserve
                # prior discussion and history
                bugzillaReopenClosedBug(bugzilla_session)

            if not test_found:
                # TODO file a new bug
                bugzillaFileNewBug(bugzilla_session)

def run():
    asyncio.run(main())

run()
