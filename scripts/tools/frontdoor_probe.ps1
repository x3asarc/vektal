[CmdletBinding()]
param(
  [string]$Domain = "app.vektal.systems",
  [string]$ExpectedIPv4 = "89.167.74.58",
  [string]$ExpectedIPv6 = "",
  [string]$OutputPath = ""
)

$ErrorActionPreference = "Continue"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
  $OutputPath = ".planning/debug/frontdoor-probe-$timestamp.txt"
}

$parent = Split-Path -Parent $OutputPath
if (-not [string]::IsNullOrWhiteSpace($parent)) {
  New-Item -ItemType Directory -Path $parent -Force | Out-Null
}

$lines = New-Object System.Collections.Generic.List[string]

function Add-Line {
  param([string]$Value)
  $lines.Add($Value)
  Write-Output $Value
}

function Write-Section {
  param([string]$Title)
  Add-Line ""
  Add-Line "## $Title"
}

function Run-Capture {
  param(
    [string]$Label,
    [scriptblock]$Action
  )

  Write-Section $Label
  try {
    $output = & $Action 2>&1
    if ($null -eq $output -or ($output -is [System.Array] -and $output.Count -eq 0)) {
      Add-Line "(no output)"
      return @()
    }

    $outLines = @()
    foreach ($entry in $output) {
      $text = "$entry"
      $outLines += $text
      Add-Line $text
    }
    return $outLines
  } catch {
    Add-Line ("ERROR: " + $_.Exception.Message)
    return @("ERROR: " + $_.Exception.Message)
  }
}

function Invoke-CurlSummary {
  param(
    [string[]]$ExtraArgs,
    [string]$TargetUrl
  )

  $args = @("-sS", "-L", "-o", "NUL", "-w", "code=%{http_code} remote_ip=%{remote_ip} tls_verify=%{ssl_verify_result} url=%{url_effective}")
  $args += $ExtraArgs
  $args += $TargetUrl

  $output = & curl.exe @args 2>&1
  return "$output"
}

Add-Line "# Frontdoor Probe"
Add-Line "timestamp_utc=$(Get-Date -Format o)"
Add-Line "domain=$Domain"
Add-Line "expected_ipv4=$ExpectedIPv4"
Add-Line "expected_ipv6=$ExpectedIPv6"

Run-Capture "Local DNS A" {
  Resolve-DnsName $Domain -Type A |
    Select-Object Name, Type, TTL, Section, IPAddress, NameHost |
    ConvertTo-Json -Depth 4
}
Run-Capture "Local DNS AAAA" {
  Resolve-DnsName $Domain -Type AAAA |
    Select-Object Name, Type, TTL, Section, IPAddress, NameHost, PrimaryServer |
    ConvertTo-Json -Depth 4
}

$resolvers = @("1.1.1.1", "8.8.8.8", "9.9.9.9")
foreach ($resolver in $resolvers) {
  Run-Capture "nslookup A via $resolver" { nslookup -type=A $Domain $resolver }
  Run-Capture "nslookup AAAA via $resolver" { nslookup -type=AAAA $Domain $resolver }
}

Run-Capture "DoH A (Cloudflare)" {
  curl.exe -sS "https://cloudflare-dns.com/dns-query?name=$Domain&type=A" -H "accept: application/dns-json"
}
Run-Capture "DoH AAAA (Cloudflare)" {
  curl.exe -sS "https://cloudflare-dns.com/dns-query?name=$Domain&type=AAAA" -H "accept: application/dns-json"
}
Run-Capture "DoH A (Google)" {
  curl.exe -sS "https://dns.google/resolve?name=$Domain&type=A"
}
Run-Capture "DoH AAAA (Google)" {
  curl.exe -sS "https://dns.google/resolve?name=$Domain&type=AAAA"
}

$probePaths = @("/", "/health", "/chat")
foreach ($path in $probePaths) {
  $url = "https://$Domain$path"
  Run-Capture "curl default $path" { Invoke-CurlSummary -ExtraArgs @("--max-time", "20") -TargetUrl $url }
}

Run-Capture "curl -4 /health" {
  Invoke-CurlSummary -ExtraArgs @("-4", "--max-time", "20") -TargetUrl "https://$Domain/health"
}

Run-Capture "curl -6 /health" {
  Invoke-CurlSummary -ExtraArgs @("-6", "--max-time", "20") -TargetUrl "https://$Domain/health"
}

if (-not [string]::IsNullOrWhiteSpace($ExpectedIPv4)) {
  Run-Capture "curl --resolve IPv4 /health" {
    Invoke-CurlSummary -ExtraArgs @("--resolve", "${Domain}:443:${ExpectedIPv4}", "--max-time", "20") -TargetUrl "https://$Domain/health"
  }
  Run-Capture "curl --resolve IPv4 /chat" {
    Invoke-CurlSummary -ExtraArgs @("--resolve", "${Domain}:443:${ExpectedIPv4}", "--max-time", "20") -TargetUrl "https://$Domain/chat"
  }
}

if (-not [string]::IsNullOrWhiteSpace($ExpectedIPv6)) {
  Run-Capture "curl --resolve IPv6 /health" {
    Invoke-CurlSummary -ExtraArgs @("--resolve", "${Domain}:443:[$ExpectedIPv6]", "--max-time", "20") -TargetUrl "https://$Domain/health"
  }
}

Write-Section "Gate"
Add-Line "Interpretation rules:"
Add-Line "1) If default /health remote_ip is not expected server IP, DNS/routing is wrong."
Add-Line "2) If default fails but --resolve IPv4 passes, client resolver path is stale/cached."
Add-Line "3) If both default and --resolve fail, origin/nginx/frontend stack is unhealthy."
Add-Line "4) If IPv6 path shows old host while IPv4 is correct, stale AAAA is the cause."

$lines | Set-Content -Path $OutputPath
Add-Line ""
Add-Line "saved_report=$OutputPath"
