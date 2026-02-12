# review

Task: `<phase>.<n>`
Owner: Reviewer
Status: `GREEN|RED`

pass_1_timestamp: `<ISO-8601>`
plan_context_opened_at: `<ISO-8601>`
pass_2_timestamp: `<ISO-8601>`

Blind-ordering-evidence: `pass_1_timestamp < plan_context_opened_at` (`Pass|Fail`)

## Findings
Use:
`[Severity] [Category] [File/Path] [Issue] [Evidence] [Required Fix]`

Example:
`[High] [Security] [src/app.py] [Unsanitized input path] [Request payload reaches filesystem call] [Validate and normalize path input]`

## Decision
1. Blocking findings present: `Yes|No`
2. Merge recommendation: `GREEN|RED`
3. Notes: `<required, use N/A if none>`

