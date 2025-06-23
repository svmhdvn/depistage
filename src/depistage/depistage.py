# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "aiohttp[speedups]"
# ]
# ///

import aiohttp
import asyncio

# TODO:
# * only works for amd64 now
# * if the same test is failing on multiple archs, file the bug as 'platform = any'

async def getLatestTestRun(session):
    url='/view/Test/job/FreeBSD-main-amd64-test/lastCompletedBuild/testReport/api/json'
    params={'tree': 'suites[cases[age,className,name,failedSince]]'}
    async with session.get(url, params=params) as resp:
        return (await resp.json())['suites'][0]['cases']

# TODO might need 'comment' field instead of 'msg'
async def getBuildMetadataKv(session, build_num):
    url = f'/view/Test/job/FreeBSD-main-amd64-test/{build_num}/api/json'
    params={'tree': 'changeSet[items[commitId,author[id],msg]]'}
    async with session.get(url, params=params) as resp:
        return (build_num, (await resp.json())['changeSet']['items'])

async def main():
    async with aiohttp.ClientSession('https://ci.freebsd.org') as session:
        j = await getLatestTestRun(session)
        unique_failed_since = frozenset(f['failedSince'] for f in j if f['failedSince'] > 0)
        print(unique_failed_since)
        buildnum_to_metadata = dict(await asyncio.gather(*(getBuildMetadataKv(session, bn) for bn in unique_failed_since)))
        print(buildnum_to_metadata)

def run():
    asyncio.run(main())

run()
