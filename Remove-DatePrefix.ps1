<#
.SYNOPSIS
    Strips the leading YYYY-MM- date prefix from post filenames in content/posts,
    renaming each via `git mv` so history follows the file.

.DESCRIPTION
    Older posts carry a date prefix (e.g. 2023-03-NTS-SPF.md) while newer ones are
    slug-only. This flattens them to one style. Runs a dry-run by default; pass
    -Execute (or use -WhatIf/-Confirm from SupportsShouldProcess) to control the
    real renames. The date is preserved in each post's TOML frontmatter, so nothing
    is lost by dropping it from the filename.

.PARAMETER PostsDir
    Directory to scan. Defaults to content/posts relative to this script.

.PARAMETER Execute
    Perform the renames. Without it, only prints what would happen.

.EXAMPLE
    .\Remove-DatePrefix.ps1
    Dry-run: list every old -> new rename without touching anything.

.EXAMPLE
    .\Remove-DatePrefix.ps1 -Execute
    Perform the renames via `git mv`.
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Medium')]
param(
    [string]$PostsDir = (Join-Path $PSScriptRoot 'content/posts'),
    [switch]$Execute
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $PostsDir)) {
    throw "Posts directory not found: $PostsDir"
}

# Whether we actually rename. -WhatIf/-Confirm are honoured by ShouldProcess below;
# -Execute is the explicit opt-in for a real run when neither is supplied.
$doRename = $Execute -or $WhatIfPreference

$renamed = 0
$skipped = 0

Get-ChildItem -LiteralPath $PostsDir -Filter '*.md' -File |
    Where-Object { $_.Name -match '^(\d{4}-\d{2}-)(.+)$' } |
    ForEach-Object {
        $newName = $matches[2]
        $dest = Join-Path $_.DirectoryName $newName

        if (Test-Path -LiteralPath $dest) {
            Write-Warning "skip (destination exists): $($_.Name)"
            $script:skipped++
            return
        }

        if (-not $doRename) {
            Write-Host "[dry-run] $($_.Name) -> $newName"
            $script:skipped++
            return
        }

        if ($PSCmdlet.ShouldProcess($_.Name, "git mv -> $newName")) {
            git mv -- $_.FullName $dest
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "git mv failed ($LASTEXITCODE): $($_.Name)"
                $script:skipped++
            }
            else {
                Write-Host "renamed: $($_.Name) -> $newName"
                $script:renamed++
            }
        }
    }

if ($doRename) {
    Write-Host "`nDone. Renamed: $renamed  Skipped: $skipped"
}
else {
    Write-Host "`nDry-run complete. Would rename: $skipped  (re-run with -Execute to apply)"
}
