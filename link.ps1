# Junction each skill into the agents' skill directories so they are
# discovered by Claude Code (~\.claude\skills) and Codex CLI (~\.agents\skills).
# Junctions work like symlinks but require no admin rights or Developer Mode.
# Run with -Remove to delete the junctions instead.
param([switch]$Remove)

$ErrorActionPreference = "Stop"
$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TargetDirs = @("$HOME\.claude\skills", "$HOME\.agents\skills")

foreach ($target in $TargetDirs) {
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    foreach ($skill in Get-ChildItem -Directory (Join-Path $RepoDir "skills")) {
        $link = Join-Path $target $skill.Name
        $existing = Get-Item $link -ErrorAction SilentlyContinue
        $isLink = $existing -and ($existing.Attributes -band [IO.FileAttributes]::ReparsePoint)
        if ($Remove) {
            if ($isLink) { $existing.Delete(); Write-Host "removed $link" }
        } else {
            if ($isLink) { $existing.Delete() }
            elseif ($existing) { Write-Host "skipped $link (exists and is not a link)"; continue }
            New-Item -ItemType Junction -Path $link -Target $skill.FullName | Out-Null
            Write-Host "linked $link -> $($skill.FullName)"
        }
    }
}
