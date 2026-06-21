# Publish amazon-sourcing to GitHub via API (when git push to github.com is blocked)
# Prerequisites:
#   1. Create empty public repo: https://github.com/new  -> name: amazon-sourcing
#   2. PAT with repo Contents write permission on that repository
#   3. Set env: GITHUB_PERSONAL_ACCESS_TOKEN

param(
    [string]$Owner = "yushuhe",
    [string]$Repo = "amazon-sourcing",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"
$token = $env:GITHUB_PERSONAL_ACCESS_TOKEN
if (-not $token) {
    $token = [System.Environment]::GetEnvironmentVariable("GITHUB_PERSONAL_ACCESS_TOKEN", "User")
}
if (-not $token) { throw "GITHUB_PERSONAL_ACCESS_TOKEN not set" }

$headers = @{
    Authorization = "Bearer $token"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

$base = Split-Path -Parent $PSScriptRoot
Set-Location $base

# Verify repo exists
try {
    Invoke-RestMethod -Uri "https://api.github.com/repos/$Owner/$Repo" -Headers $headers | Out-Null
} catch {
    throw "Repository $Owner/$Repo not found. Create it at https://github.com/new first."
}

function ApiPost($path, $body) {
    Invoke-RestMethod -Method Post -Uri "https://api.github.com$path" -Headers $headers -Body ($body | ConvertTo-Json -Depth 20) -ContentType "application/json; charset=utf-8"
}

$files = git ls-files
$tree = @()
foreach ($rel in $files) {
    $full = Join-Path $base $rel
  if (-not (Test-Path $full)) { continue }
    $bytes = [System.IO.File]::ReadAllBytes($full)
    $blob = ApiPost "/repos/$Owner/$Repo/git/blobs" @{ content = [Convert]::ToBase64String($bytes); encoding = "base64" }
    $tree += @{ path = $rel.Replace("\", "/"); mode = "100644"; type = "blob"; sha = $blob.sha }
    Write-Host "  blob: $rel"
}

$treeResp = ApiPost "/repos/$Owner/$Repo/git/trees" @{ tree = $tree }
$commit = ApiPost "/repos/$Owner/$Repo/git/commits" @{
    message = "Initial open-source release via API"
    tree = $treeResp.sha
}
try {
    ApiPost "/repos/$Owner/$Repo/git/refs" @{ ref = "refs/heads/$Branch"; sha = $commit.sha }
} catch {
    Invoke-RestMethod -Method Patch -Uri "https://api.github.com/repos/$Owner/$Repo/git/refs/heads/$Branch" -Headers $headers -Body (@{ sha = $commit.sha; force = $true } | ConvertTo-Json) -ContentType "application/json"
}

Write-Host ""
Write-Host "Done: https://github.com/$Owner/$Repo"
