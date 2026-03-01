# Structure Audit: 14.2-05 - compact_output Mode + Edge-Type Scoring

## 1. Directory Structure
- [x] Does the change respect the directory structure?
- [x] Is the code modular and well-organized?

## 2. File Organization
- [x] Are the files in the correct directories?
- [x] Is the file organization consistent with the codebase?

## 3. Module Hierarchy
- [x] Are the modules correctly organized?
- [x] Is the module hierarchy consistent with the codebase?

## Summary
The changes are well-integrated into the existing graph retrieval pipeline:
- `src/graph/search_expand_bridge.py`: Core scoring and serialization logic
- `src/graph/query_interface.py`: Interface updates for parameter propagation
- `src/graph/mcp_server.py`: Schema and handler updates
- `tests/graph/`: Unit tests for scoring and compact mode
