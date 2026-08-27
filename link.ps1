# Junction each skill into the agents' skill directories so they are
# discovered by Claude Code (~\.claude\skills) and Codex CLI (~\.agents\skills).
# Junctions work like symlinks but require no admin rights or Developer Mode.
# Run with -Remove to delete the junctions instead.
# CmdletBinding makes this an advanced script so unknown arguments are
# rejected instead of silently collecting in $args.
[CmdletBinding()]
param([switch]$Remove)

$ErrorActionPreference = "Stop"
$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallHome = if ($env:CONDUCTOR_HOME) { $env:CONDUCTOR_HOME } else { $HOME }
$TargetDirs = @("$InstallHome\.claude\skills", "$InstallHome\.agents\skills")

$Skills = @(Get-ChildItem -Directory (Join-Path $RepoDir "skills"))
if ($Skills.Count -eq 0) {
    throw "no skills found in $RepoDir\skills (incomplete checkout?)"
}

foreach ($target in $TargetDirs) {
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    foreach ($skill in $Skills) {
        $link = Join-Path $target $skill.Name
        $existing = Get-Item $link -ErrorAction SilentlyContinue
        $isLink = $existing -and ($existing.Attributes -band [IO.FileAttributes]::ReparsePoint)
        $isManaged = $isLink -and ($existing.Target -eq $skill.FullName)
        if ($Remove) {
            if ($isManaged) { $existing.Delete(); Write-Host "removed $link" }
            elseif ($isLink) { Write-Warning "skipped $link (link is not managed by this checkout)" }
        } else {
            if ($isManaged) { $existing.Delete() }
            elseif ($isLink) { Write-Warning "skipped $link (link is not managed by this checkout)"; continue }
            elseif ($existing) { Write-Host "skipped $link (exists and is not a link)"; continue }
            New-Item -ItemType Junction -Path $link -Target $skill.FullName | Out-Null
            Write-Host "linked $link -> $($skill.FullName)"
        }
    }
}
