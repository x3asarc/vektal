param(
  [Parameter(Mandatory = $true)]
  [string]$BaseUrl,

  [Parameter(Mandatory = $true)]
  [string]$RoutesFile,

  [Parameter(Mandatory = $true)]
  [string]$RunId
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Normalize-Route {
  param([string]$Route)
  if ([string]::IsNullOrWhiteSpace($Route)) { return "/" }
  if ($Route.StartsWith("http://") -or $Route.StartsWith("https://")) { return $Route }
  if (-not $Route.StartsWith("/")) { return "/$Route" }
  return $Route
}

function Slugify-Route {
  param([string]$Route)
  $slug = $Route.Trim("/")
  if ([string]::IsNullOrWhiteSpace($slug)) { return "home" }
  $slug = $slug -replace "[^a-zA-Z0-9\-_/]", ""
  $slug = $slug -replace "/", "__"
  return $slug.ToLowerInvariant()
}

function Resolve-Routes {
  param([string]$Path)
  $raw = Get-Content -Path $Path -Raw
  $json = $raw | ConvertFrom-Json

  if ($json -is [System.Array]) {
    if ($json.Count -eq 0) { return @("/") }
    if ($json[0] -is [string]) { return $json }
    if ($json[0].PSObject.Properties.Name -contains "route") {
      return @($json | ForEach-Object { $_.route })
    }
  }

  if ($json.PSObject.Properties.Name -contains "pages") {
    return @($json.pages | ForEach-Object { $_.route })
  }

  throw "Unsupported routes JSON format in $Path"
}

if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
  throw "npx is required for Playwright screenshots."
}

if (-not (Get-Command firecrawl -ErrorAction SilentlyContinue)) {
  throw "firecrawl CLI is required for Firecrawl capture."
}

$routes = Resolve-Routes -Path $RoutesFile | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique
if ($routes.Count -eq 0) {
  throw "No routes found in $RoutesFile"
}

$root = ".planning/page-audit/$RunId"
$pwDir = "$root/captures/playwright"
$fcDir = "$root/captures/firecrawl"
$manifestPath = "$root/captures/manifest.json"

New-Item -ItemType Directory -Path $pwDir -Force | Out-Null
New-Item -ItemType Directory -Path $fcDir -Force | Out-Null

$manifest = @()

foreach ($route in $routes) {
  $normalized = Normalize-Route -Route $route
  $slug = Slugify-Route -Route $normalized
  $url = if ($normalized.StartsWith("http://") -or $normalized.StartsWith("https://")) { $normalized } else { "$BaseUrl$normalized" }

  $desktopPath = "$pwDir/$slug-desktop.png"
  $mobilePath = "$pwDir/$slug-mobile.png"
  $firecrawlPath = "$fcDir/$slug.json"

  $entry = [ordered]@{
    route = $normalized
    url = $url
    playwright_desktop = $desktopPath
    playwright_mobile = $mobilePath
    firecrawl_output = $firecrawlPath
    playwright_desktop_status = "pending"
    playwright_mobile_status = "pending"
    firecrawl_status = "pending"
    errors = @()
  }

  try {
    & npx playwright screenshot --device="Desktop Chrome" "$url" "$desktopPath" | Out-Null
    $entry.playwright_desktop_status = "ok"
  } catch {
    $entry.playwright_desktop_status = "error"
    $entry.errors += "desktop screenshot failed: $($_.Exception.Message)"
  }

  try {
    & npx playwright screenshot --device="iPhone 14" "$url" "$mobilePath" | Out-Null
    $entry.playwright_mobile_status = "ok"
  } catch {
    $entry.playwright_mobile_status = "error"
    $entry.errors += "mobile screenshot failed: $($_.Exception.Message)"
  }

  try {
    & firecrawl scrape "$url" --format markdown,links,screenshot -o "$firecrawlPath" | Out-Null
    $entry.firecrawl_status = "ok"
  } catch {
    $entry.firecrawl_status = "error"
    $entry.errors += "firecrawl scrape failed: $($_.Exception.Message)"
  }

  $manifest += [pscustomobject]$entry
}

$manifestJson = $manifest | ConvertTo-Json -Depth 8
Set-Content -Path $manifestPath -Value $manifestJson
Write-Output "Capture complete. Manifest: $manifestPath"

