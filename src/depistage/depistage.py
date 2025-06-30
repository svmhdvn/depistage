# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "aiohttp[speedups]"
# ]
# ///

import aiohttp
import asyncio
import pathlib
import itertools

# TODO:
# * only works for amd64 now
# * if the same test is failing on multiple archs, file the bug as 'platform = any'

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
    failed_tests = [t for t in j if t['failedSince'] > 0]
    unique_failed_since = frozenset(t['failedSince'] for t in failed_tests)
    buildnum_to_metadata = dict(await asyncio.gather(*(jenkinsBuildMetadataKv(session, bn) for bn in unique_failed_since)))
    kf = lambda t: t['className']
    failed_kyua_suites = [{'name': k, 'cases': list(v)} for k, v in itertools.groupby(sorted(failed_tests, key=kf), key=kf)]
    return {'failed_kyua_suites': failed_kyua_suites, 'past_builds': buildnum_to_metadata}

async def bugzillaSearchExistingBugs(session, api_key):
    url = '/bugzilla/rest/bug'
    params = {
        'api_key': api_key,
        'keywords': 'ci',
        'status': ['New', 'Open', 'In Progress'],
    }
    async with session.get(url, params=params) as resp:
        return (await resp.json())['bugs']

async def bugzillaFileBug(session, api_key, jenkins_data, suite):
    url = '/bugzilla/rest/bug'
    params = {
        'api_key': api_key,
        'keywords': 'ci',
        'status': ['New', 'Open', 'In Progress'],
    }
    async with session.post(url, json=params) as resp:
        return (await resp.json())['bugs']

async def fetchBugzillaData(session, api_key):
    existing_bugs = await bugzillaSearchExistingBugs(session, api_key)
    return {'existing_bugs': existing_bugs}

async def triageFailingKyuaSuite(session, bugzilla_data, jenkins_data, suite):
    for b in bugzilla_data['existing_bugs']:
        if suite['name'] in b['summary']:
            return

    print(f"need to file: {suite['name']}\tcases: {suite['cases']}")


async def asyncMain():
    api_key = pathlib.Path('/home/siva/src/playground/bugstest_apikey.txt').read_text()

    # TODO change to production bugzilla URL once ready
    async with (
        aiohttp.ClientSession('https://ci.freebsd.org') as jenkins_session,
        aiohttp.ClientSession('https://bugstest.freebsd.org') as bugzilla_session
    ):

        jenkins_data, bugzilla_data = await asyncio.gather(
            fetchJenkinsData(jenkins_session),
            fetchBugzillaData(bugzilla_session, api_key),
        )

        await asyncio.gather(*(
            triageFailingKyuaSuite(bugzilla_session, bugzilla_data, jenkins_data, s)
            for s in jenkins_data['failed_kyua_suites']
        ))

def main():
    asyncio.run(asyncMain())

main()
