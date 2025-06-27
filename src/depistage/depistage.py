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

async def jenkinsLatestTestRun(session):
    url='/view/Test/job/FreeBSD-main-amd64-test/lastCompletedBuild/testReport/api/json'
    params={'tree': 'suites[cases[age,className,name,failedSince]]'}
    async with session.get(url, params=params) as resp:
        return (await resp.json())['suites'][0]['cases']

# TODO might need 'comment' field instead of 'msg'
async def jenkinsBuildMetadataKv(session, build_num):
    url = f'/view/Test/job/FreeBSD-main-amd64-test/{build_num}/api/json'
    params={'tree': 'changeSet[items[commitId,author[id],msg]]'}
    async with session.get(url, params=params) as resp:
        return (build_num, (await resp.json())['changeSet']['items'])

async def fetchJenkinsData():
    async with aiohttp.ClientSession('https://ci.freebsd.org') as session:
        j = await jenkinsLatestTestRun(session)
        unique_failed_since = frozenset(f['failedSince'] for f in j if f['failedSince'] > 0)
        buildnum_to_metadata = dict(await asyncio.gather(*(jenkinsBuildMetadataKv(session, bn) for bn in unique_failed_since)))
        return ('jenkins', {'tests': j, 'past_builds': buildnum_to_metadata})

async def bugzillaSearchExistingBugs(session, api_key):
    url = '/bugzilla/rest/bug'
    params={'api_key': api_key, 'keywords': 'ci'}
    async with session.get(url, params=params) as resp:
        return (await resp.json())['bugs']

# TODO change to production URL once ready
async def fetchBugzillaData(api_key):
    async with aiohttp.ClientSession('https://bugstest.freebsd.org') as session:
        existing_bugs = await bugzillaSearchExistingBugs(session, api_key)
        return ('bugzilla', {'existing_bugs': existing_bugs})

async def main():
    api_key = pathlib.Path('/home/siva/src/playground/bugstest_apikey.txt').read_text()
    all_data = dict(await asyncio.gather(
        #fetchJenkinsData(),
        fetchBugzillaData(api_key),
    ))
    print(all_data['bugzilla'])

def run():
    asyncio.run(main())

run()
