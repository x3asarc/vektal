
import asyncio
import inspect
from neo4j import AsyncGraphDatabase, GraphDatabase
import os

async def debug_drivers():
    # Sync driver
    uri = "bolt://localhost:7687"
    auth = ("neo4j", "password")
    sync_driver = GraphDatabase.driver(uri, auth=auth)
    print(f"Sync Driver: {type(sync_driver).__name__}")
    print(f"Sync session is coroutine function: {asyncio.iscoroutinefunction(sync_driver.session)}")
    s = sync_driver.session()
    print(f"Sync session object: {type(s).__name__}")
    print(f"Sync session has __aenter__: {hasattr(s, '__aenter__')}")
    sync_driver.close()

    # Async driver
    async_driver = AsyncGraphDatabase.driver(uri, auth=auth)
    print(f"
Async Driver: {type(async_driver).__name__}")
    print(f"Async session is coroutine function: {asyncio.iscoroutinefunction(async_driver.session)}")
    # We can't call session() easily without connection but let's try to see if it's a coroutine
    print(f"Async session is coroutine: {inspect.iscoroutine(async_driver.session())}")
    await async_driver.close()

if __name__ == "__main__":
    try:
        asyncio.run(debug_drivers())
    except Exception as e:
        print(f"Error: {e}")
