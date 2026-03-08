# scripts/get-frontend-context.ps1
# Automates frontend discovery via the Knowledge Graph and local scans.

param(
    [string]$FeatureName = "",
    [string]$ComponentPath = ""
)

Write-Host "=== Frontend Design Skill: Graph-Aware Discovery ===" -ForegroundColor Cyan

# 1. Try to find the Feature/Planning context in Neo4j
if ($FeatureName) {
    Write-Host "Searching for feature context: $FeatureName..."
    # We use a simple python bridge to query our query_templates
    python -c "
from src.graph.query_templates import execute_template
import json
import os
params = {'phase': '$FeatureName'}
# Try phase lookup first
results = execute_template('phase_code', params)
if not results:
    # Try semantic search if phase number not provided
    params = {'query': '$FeatureName', 'top_k': 5}
    results = execute_template('tool_search_text', params)
print(json.dumps(results))
"
}

# 2. Map local CSS variables and tokens
Write-Host "`nScanning for Design Tokens (globals.css)..." -ForegroundColor Yellow
$globalsPath = Get-ChildItem -Recurse -Filter "globals.css" | Select-Object -First 1
if ($globalsPath) {
    Write-Host "Found: $($globalsPath.FullName)"
    $content = Get-Content $globalsPath.FullName
    $vars = $content | Select-String "--[\w-]+:"
    Write-Host "Extracted $($vars.Count) CSS variables."
    $vars | Select-Object -First 10 | ForEach-Object { Write-Host "  $($_.Line.Trim())" }
}

# 3. Component Dependency Scan (Imports)
if ($ComponentPath -and (Test-Path $ComponentPath)) {
    Write-Host "`nMapping Dependencies for: $ComponentPath" -ForegroundColor Yellow
    # Using a simpler string-based filter to avoid regex parsing issues
    Get-Content $ComponentPath | Where-Object { $_ -match "import .* from" } | ForEach-Object {
        Write-Host "  $($_.Trim())"
    }
}

Write-Host "`nDiscovery Complete." -ForegroundColor Green
