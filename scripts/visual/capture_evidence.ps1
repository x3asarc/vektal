param(
  [Parameter(Mandatory = $true)]
  [string]$BaseUrl,

  [Parameter(Mandatory = $true)]
  [string]$RunId,

  [string]$RoutesFile = ".planning/active_routes.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Ensure directories exist
$root = ".planning/ooda-audit/$RunId"
$pwDir = "$root/captures/playwright"
$fcDir = "$root/captures/firecrawl"
New-Item -ItemType Directory -Path $pwDir, $fcDir -Force | Out-Null

# Resolve routes (default to home if file missing)
$routes = @("/")
if (Test-Path $RoutesFile) {
    $raw = Get-Content -Path $RoutesFile -Raw
    $json = $raw | ConvertFrom-Json
    if ($json -is [System.Array]) { $routes = $json }
    elseif ($json.PSObject.Properties.Name -contains "routes") { $routes = $json.routes }
}

# MANDATORY: Add Anchor Pages for consistency audit
$anchors = @("/dashboard", "/search", "/chat", "/enrichment")
foreach ($a in $anchors) {
    if ($routes -notcontains $a) {
        $routes += $a
        Write-Host "[OODA] Adding Anchor Page: $a" -ForegroundColor Gray
    }
}

Write-Host "[OODA] Capturing evidence for $($routes.Count) routes..." -ForegroundColor Cyan

foreach ($route in $routes) {
    $url = if ($route.StartsWith("http")) { $route } else { "$BaseUrl$route" }
    $slug = $route.Trim("/").Replace("/", "__")
    if ([string]::IsNullOrWhiteSpace($slug)) { $slug = "home" }

    Write-Host "[OODA] Processing: $url"

    # 1. Playwright Desktop
    try {
        & npx playwright screenshot --device="Desktop Chrome" "$url" "$pwDir/$slug-desktop.png" | Out-Null
    } catch {
        Write-Warning "Desktop screenshot failed for $url"
    }

    # 2. Playwright Mobile
    try {
        & npx playwright screenshot --device="iPhone 14" "$url" "$pwDir/$slug-mobile.png" | Out-Null
    } catch {
        Write-Warning "Mobile screenshot failed for $url"
    }

    # 3. Firecrawl Scrape
    try {
        & firecrawl scrape "$url" --format markdown,screenshot -o "$fcDir/$slug.json" | Out-Null
    } catch {
        Write-Warning "Firecrawl scrape failed for $url"
    }
}

Write-Host "[OODA] Evidence capture complete. Results in $root" -ForegroundColor Green
