import inspect
try:
    import neo4j._async.driver
    from neo4j._async.driver import AsyncDriver
    print("AsyncDriver.execute_query signature:")
    print(inspect.signature(AsyncDriver.execute_query))
except Exception as e:
    print(f"Error: {e}")
