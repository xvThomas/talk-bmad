#!/usr/bin/env pwsh
#
# link-skills.ps1 — Canonical skill linker for the talk project (bmad hub).
#
# Claude Code only discovers skills under `.claude\skills\`. This script
# populates `.claude\skills\` in the CURRENT directory with one link per skill
# folder, drawing from:
#   1. the bmad hub skills (always: talk-bmad\.agents\skills\*)
#   2. any extra `.agents\skills` roots passed as -ExtraRoots (repo-local skills)
#
# On Windows it uses directory JUNCTIONS (no admin / developer mode required).
# On Linux/macOS pwsh it falls back to symlinks. Bash users: run link-skills.sh.
#
# Usage (run from the target repo root):
#   talk-bmad     : pwsh ..\talk-bmad\scripts\link-skills.ps1
#   talk-backend  : pwsh ..\talk-bmad\scripts\link-skills.ps1 -ExtraRoots .agents\skills
#   talk-ui       : pwsh ..\talk-bmad\scripts\link-skills.ps1 -ExtraRoots .agents\skills
#
# `.claude\skills\` is machine-local (links) and must stay gitignored.

param([string[]]$ExtraRoots = @())

$ErrorActionPreference = 'Stop'

$BmadSkills = Join-Path $PSScriptRoot '..\.agents\skills'
$Dest = '.claude/skills'
$LinkType = if ($IsWindows -or ($null -eq $IsWindows)) { 'Junction' } else { 'SymbolicLink' }

New-Item -ItemType Directory -Force -Path $Dest | Out-Null

function Link-From($src) {
  if (-not (Test-Path $src)) { Write-Host "skip (missing): $src"; return }
  $srcPath = (Resolve-Path $src).Path
  Get-ChildItem -Path $srcPath -Directory | ForEach-Object {
    $name = $_.Name
    $target = Join-Path $Dest $name
    if (Test-Path $target) { Remove-Item $target -Recurse -Force }
    New-Item -ItemType $LinkType -Path $target -Target $_.FullName | Out-Null
    Write-Host "linked: $name -> $($_.FullName)"
  }
}

# 1. bmad hub skills (always)
Link-From $BmadSkills

# 2. repo-local skill roots (extra arguments)
foreach ($root in $ExtraRoots) { Link-From $root }

Write-Host "Done. $Dest populated. Reload the Claude Code window to pick up new skills."
