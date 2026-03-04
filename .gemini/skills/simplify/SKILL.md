---
name: simplify
description: Reviews your recently changed files for code reuse, quality, and efficiency issues, then fixes them. Run it after implementing a feature or bug fix to clean up your work. Use when the user asks to simplify code, clean up their changes, review recent work, or improve code quality. Make sure to use this skill whenever the user mentions simplify, cleanup, code review, refactor, or wants to improve their recent changes.
---

# Simplify Skill

Reviews recently changed files for code reuse, quality, and efficiency issues, then applies fixes automatically.

## Core Philosophy: Simplicity First

**The primary goal is to make code shorter, simpler, and more maintainable.**

When reviewing code:
- **Shorter is better** - If a file can be reduced in length without losing functionality, do it
- **Refactoring is paramount** - Actively look for opportunities to consolidate, extract, and simplify
- **Delete before you add** - Removing unnecessary code is more valuable than adding new abstractions
- **Prefer clarity over cleverness** - Simple, obvious code beats clever, compact code

Every agent should ask: "How can this code be made simpler and shorter?"

## When to use this skill

- After implementing a feature or bug fix
- When the user asks to clean up or simplify their code
- When the user wants to review and improve recent changes
- When the user wants to refactor or optimize their work

## How it works

This skill spawns three specialized review agents in parallel to analyze your changed files.

**DEFAULT METHOD: Uses Neo4j/Graphiti knowledge graph** to trace code relationships, dependencies, and recent changes. Graph queries reveal:
- What imports/calls what (actual vs expected linkages)
- Files that changed together recently (co-change patterns)
- Similar code patterns (what's used vs what's orphaned)
- Impact radius (what depends on each file)

**The three review agents:**
1. **Code Reuse Agent** - Identifies duplication and opportunities to extract common logic, **shortening files**
2. **Code Quality Agent** - Reviews clarity, naming, structure, and **opportunities to simplify/reduce code** (uses graph to investigate dead code)
3. **Efficiency Agent** - Looks for performance issues and **unnecessary complexity that can be removed**

After all agents complete their reviews, their findings are aggregated and fixes are applied to the codebase.

## Optional focus areas

The user can provide optional focus text to emphasize specific concerns. When provided, ensure all three agents pay special attention to the focus area, but still perform their full review.

Examples:
- "focus on memory efficiency" - all agents prioritize memory-related issues
- "focus on code reuse" - all agents emphasize finding duplication
- "focus on readability" - all agents emphasize code clarity and naming

## Execution steps

1. **Identify changed files and load graph context**
   - Run `git status --short` to get recently modified files
   - Filter out non-code files (configs, markdown, etc. unless they contain logic worth reviewing)
   - **Query the knowledge graph for context:**
     ```python
     from src.graph.query_interface import query_graph

     # For each changed file, get its connections:
     for file_path in changed_files:
         # What imports this file (dependencies)
         importers = query_graph("imported_by", {"file_path": file_path})

         # What this file imports
         imports = query_graph("imports", {"file_path": file_path})

         # Impact radius (what would break if we change this)
         impact = query_graph("impact_radius", {"file_path": file_path})

         # Similar files (co-change patterns, related code)
         similar = query_graph("similar_files", {"file_path": file_path, "limit": 5, "threshold": 0.7})
     ```
   - If no changed files, inform the user and exit

2. **Spawn three parallel review agents**
   - Use the Task tool with `subagent_type: "general-purpose"` for each agent
   - Launch all three in the same message (parallel execution)
   - Pass the list of changed files to each agent
   - Include any focus area in each agent's prompt

   **Code Reuse Agent prompt:**
   ```
   Review the following changed files for code reuse opportunities and simplification through refactoring:

   Files: [list of files]

   Focus: [user's focus area if provided]

   PRIMARY GOAL: Make code shorter and simpler by eliminating duplication and extracting reusable logic.

   Your task:
   1. Read each changed file
   2. Identify duplicated code patterns that can be consolidated
   3. Find opportunities to extract common logic into shared functions/classes
   4. Look for repeated business logic that could be centralized
   5. Check for similar patterns that could use the same abstraction
   6. **Prioritize changes that will shorten files and reduce total line count**
   7. Look for boilerplate that can be eliminated through better abstractions

   Return a JSON report with this structure:
   {
     "findings": [
       {
         "file": "path/to/file",
         "issue": "description of duplication/reuse opportunity",
         "severity": "high|medium|low",
         "suggested_fix": "how to extract and reuse the logic",
         "lines_saved": "estimated number of lines this will remove"
       }
     ]
   }
   ```

   **Code Quality Agent prompt:**
   ```
   Review the following changed files for code quality issues and simplification opportunities:

   Files: [list of files]

   Focus: [user's focus area if provided]

   PRIMARY GOAL: Make code simpler, clearer, and shorter through aggressive refactoring.

   Your task:
   1. Read each changed file
   2. **Look for verbose code that can be simplified or condensed**
   3. **Identify overly complex functions that can be simplified (not just split)**
   4. Find unnecessary abstractions or indirection that add bloat
   5. **CRITICAL - Dead code investigation protocol (USE GRAPH QUERIES):**
      When you find unused code, DO NOT just suggest deletion. Use Neo4j/Graphiti graph queries to trace linkages:

      **PRIMARY METHOD - Query the knowledge graph:**
      ```python
      from src.graph.query_interface import query_graph

      # For unused function - find who SHOULD call it:
      result = query_graph("function_callers", {"function_name": "unused_function_name"})
      # Returns: callers or empty if genuinely unused

      # For unused file - trace import dependencies:
      result = query_graph("imported_by", {"file_path": "path/to/file.py"})
      # Shows what files import this (or should import it)

      # Find similar patterns being used:
      result = query_graph("similar_files", {"file_path": "path/to/file.py", "limit": 5, "threshold": 0.7})
      # Returns semantically similar files - compare usage patterns

      # Trace impact radius (what depends on this):
      result = query_graph("impact_radius", {"file_path": "path/to/file.py"})
      # Shows dependency chain 1-3 levels deep
      ```

      **Investigation steps:**
      a) **Query graph for linkages** - use `function_callers`, `imported_by`, `impact_radius` queries first
      b) **Check recent changes** - query graph for files that changed together recently
      c) **Find similar patterns** - use `similar_files` to see what IS being used
      d) **Trace the call chain** - follow graph edges from entry points
      e) **Classify the dead code**:
         - Genuinely dead (graph shows zero references) → safe to delete
         - Incomplete integration (graph shows it SHOULD be connected) → wire it up
         - Replaced by alternative (graph shows newer pattern) → document why
         - Future feature stub (no graph connections yet) → mark clearly
      f) **Report full investigation** with graph query results, not just "delete this"

      **Fallback:** If graph is unavailable, use grep/file search as secondary method
   6. Check variable/function naming for clarity (shorter is better when still clear)
   7. Find inconsistencies with the codebase's existing patterns
   8. **Prioritize changes that reduce line count and cognitive complexity**

   Return a JSON report with this structure:
   {
     "findings": [
       {
         "file": "path/to/file",
         "issue": "description of quality/simplification opportunity",
         "severity": "high|medium|low",
         "suggested_fix": "specific simplification to apply",
         "lines_saved": "estimated number of lines this will remove",
         "investigation": "for dead code: full trace of where it should be called, why it's not, and what should happen"
       }
     ]
   }
   ```

   **Efficiency Agent prompt:**
   ```
   Review the following changed files for efficiency issues and unnecessary complexity:

   Files: [list of files]

   Focus: [user's focus area if provided]

   PRIMARY GOAL: Remove unnecessary complexity and make code more efficient through simplification.

   Your task:
   1. Read each changed file
   2. **Find over-engineered solutions that can be simplified**
   3. Look for inefficient algorithms or data structures
   4. Identify unnecessary loops or redundant operations that can be removed
   5. Check for memory leaks or excessive memory usage
   6. Find database queries that could be optimized or eliminated
   7. Look for I/O operations that could be batched, cached, or removed
   8. **Identify premature optimizations or abstractions that add complexity without benefit**

   Return a JSON report with this structure:
   {
     "findings": [
       {
         "file": "path/to/file",
         "issue": "description of efficiency/complexity issue",
         "severity": "high|medium|low",
         "suggested_fix": "specific optimization or simplification to apply",
         "lines_saved": "estimated number of lines this will remove"
       }
     ]
   }
   ```

3. **Wait for all agents to complete**
   - All three agents run in parallel
   - Collect results from each agent

4. **Aggregate findings**
   - Combine all findings from the three agents
   - Remove duplicate findings (same file + similar issue)
   - Prioritize by severity: high → medium → low
   - Group findings by file for easier application

5. **Apply fixes**
   - For each file with findings, starting with high severity:
     - Read the current file content
     - Apply suggested fixes using the Edit tool
     - Ensure fixes don't conflict with each other
     - Prioritize correctness over aggressive optimization

   - For complex fixes (like extracting shared logic):
     - Create new helper functions/modules as needed
     - Update all affected files to use the new abstractions

   - After applying fixes to each file:
     - Run relevant tests if available (pytest for Python, npm test for TypeScript/JS)
     - If tests fail, revert the change and note the issue

6. **Report results**
   - Summarize what was reviewed (file count, line count)
   - List all findings by category (reuse, quality, efficiency)
   - Report what fixes were applied successfully
   - Note any fixes that couldn't be applied automatically
   - Include test results if tests were run

## Important guidelines

- **Use the graph first:** ALWAYS query Neo4j/Graphiti knowledge graph before making decisions. The graph shows actual vs expected linkages, recent co-changes, and impact radius. Graph queries are the PRIMARY method, not grep.
- **Simplify aggressively:** The goal is to make code shorter and simpler. When in doubt, choose the solution that removes more lines.
- **Refactor boldly:** Don't just identify issues—actively refactor to consolidate, extract, and simplify.
- **Investigate before deleting:** CRITICAL - Never just delete "dead" code without graph investigation. Query `function_callers`, `imported_by`, and `impact_radius` to trace where it should be called, why it's not being used, and whether it represents incomplete integration or a genuine dead end. Report the full investigation with graph results.
- **Delete ruthlessly (but wisely):** After graph investigation, remove genuinely dead code (zero graph references), unnecessary abstractions, and redundant logic. But know WHY it's safe to delete based on graph evidence.
- **Shorter is better:** If functionality can be preserved with fewer lines, that's the right choice.
- **Safety first:** Never apply a fix that breaks tests. If uncertain, describe the finding and let the user decide.
- **Focus on substance:** Prioritize meaningful improvements (correctness, performance, maintainability) over cosmetic changes.
- **Test after changes:** Always run tests after applying fixes to ensure nothing broke.

## Example usage scenarios

**Basic usage:**
```
User: "simplify"
Result: Reviews all changed files, spawns 3 agents, applies fixes
```

**With focus:**
```
User: "simplify focus on memory efficiency"
Result: All agents emphasize memory-related issues while still doing full review
```

**After feature work:**
```
User: "I just added the export feature, can you simplify the code?"
Result: Reviews changed files from the export feature work and applies improvements
```

## Edge cases

- **No changed files:** Inform user there's nothing to review
- **Only config/doc changes:** Let user know these don't typically need code review
- **Very large changeset (>20 files):** Ask user if they want to review all or focus on specific files
- **Test failures after fixes:** Revert the problematic change and report what couldn't be applied
- **Conflicting suggestions:** Prioritize correctness > performance > style

## Output format

Present results in this structure:

```markdown
# Simplify Results

## Summary
- Files reviewed: X
- Total lines before: Y
- Total lines after: Z
- **Lines removed: (Y - Z)**
- Findings: N (A high, B medium, C low)
- Fixes applied: M

## Code Reuse Findings
[List findings from code reuse agent with lines_saved for each]

## Code Quality Findings
[List findings from quality agent with lines_saved for each]

## Efficiency Findings
[List findings from efficiency agent with lines_saved for each]

## Applied Fixes
- [file path]: [description of fix] (-X lines)
- [file path]: [description of fix] (-Y lines)

## Could Not Apply
- [file path]: [reason why fix wasn't applied]

## Test Results
[Results from running tests after fixes]

## Impact
**Total reduction: N lines removed (X% reduction)**
```
