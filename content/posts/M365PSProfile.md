+++
title = 'M365PSProfile: Keeping the Microsoft 365 Admin Modules Up to Date'
date = '2026-07-04T14:23:29+02:00'
draft = true
description = "A PowerShell module that installs and updates the usual Microsoft 365 admin modules from the PowerShell profile - what it does, how it works inside, and what to watch for"
tags = ["powershell", "microsoft-365", "powershell-profile", "psresourceget", "exchange-online", "microsoft-graph"]
categories = ["PowerShell"]
+++

## The Discovery

Every Microsoft 365 admin machine slowly collects PowerShell modules: `ExchangeOnlineManagement`, `Microsoft.Graph`, `MicrosoftTeams`, `PnP.PowerShell`, and a few more. Each one has its own release rhythm, and sooner or later one of them is two major versions behind and breaks a script in a funny way. The usual cure is a block of `Install-Module` / `Update-Module` lines somewhere in the profile, which nobody likes to maintain.

**M365PSProfile** is a module which takes over exactly that job. It is published in the PowerShell Gallery by Andres Bohren and Fabrice Reiser, and it describes itself as a helper that keeps the PowerShell modules a Microsoft 365 administrator needs up to date.

> **NEEDS YOUR LAB:** the personal part - where you met the module (Andres' blog? a conference?), what you used before for keeping modules current, and what made you try it.

## What Is M365PSProfile?

The authors started with a profile script that installed the modules. Over time it became hard to manage, so they moved the logic into a module that is updated through the PowerShell Gallery, and what remained in the profile is a one-liner. Their goals, as published on the project page:

- a simple one-liner in the PowerShell profile
- no admin rights needed: modules go to the `CurrentUser` scope
- predefined module list, or your own list through a parameter
- works with Windows PowerShell 5.1 and PowerShell 7
- uses `Microsoft.PowerShell.PSResourceGet` instead of the older PowerShellGet

The module is open source (GPL-3.0 according to the GitHub repository), and the Gallery lists version 0.9.1 as the current one, with a history going back to the first previews in late 2023.

## Installation and First Run

Installation is a normal Gallery install:

```powershell
# PSResourceGet
Install-PSResource -Name M365PSProfile -Scope CurrentUser

# or the old PowerShellGet
Install-Module -Name M365PSProfile -Scope CurrentUser

Get-Command -Module M365PSProfile
```

The package declares `Microsoft.PowerShell.PSResourceGet` (1.2.0 or later for 0.9.1) as a dependency. PowerShell 7.4 already ships it; on Windows PowerShell 5.1 it has to come from the Gallery.

To see what the module would install, ask for the standard list:

```powershell
Get-M365StandardModule
```

In version 0.9.1 the list contains 17 modules:

| Area | Modules |
|---|---|
| Exchange Online | `ExchangeOnlineManagement`, `Icewolf.EXO.SpamAnalyze` |
| Teams | `MicrosoftTeams` |
| SharePoint | `Microsoft.Online.SharePoint.PowerShell`, `PnP.PowerShell` |
| Security and compliance | `ORCA` (Defender for Office 365 configuration analyzer) |
| Graph and Entra | `Microsoft.Graph`, `Microsoft.Graph.Beta`, `Microsoft.Entra`, `Microsoft.Entra.Beta`, `MSIdentityTools`, `PSMSALNet` |
| Other admin areas | `O365CentralizedAddInDeployment`, `MSCommerce`, `WhiteboardAdmin`, `MicrosoftPlaces` |
| The module itself | `M365PSProfile` |

Yes, the module keeps itself on the list too.

> **NEEDS YOUR LAB:** the output of the first `Install-M365Module` run on a lab machine - ASCII banner, the per-module status lines, how long it took (screenshot or pasted text). A second run, when everything is already current, would show the "up to date" case.

## The Profile One-Liner

The point of the module is the profile. If there is no profile yet, one command writes it:

```powershell
Add-M365PSProfile
```

If a profile already exists, the same command appends the block, unless it already finds an `Install-M365Module` line - then it reports that and changes nothing. The block it writes is just two lines (plus a comment):

```powershell
Import-Module -Name M365PSProfile
Install-M365Module
```

Windows PowerShell 5.1 and PowerShell 7 use different profile files (`WindowsPowerShell` and `PowerShell` folders under Documents), so the setup has to be done once in each. Since version 0.9.1 `Add-M365PSProfile` also has a `-ProfileType` parameter that follows the `$PROFILE` properties, so the block can go to another profile:

```powershell
Add-M365PSProfile -ProfileType AllUsersCurrentHost
```

To customize the list, pass `-Modules` to `Install-M365Module`:

```powershell
Install-M365Module -Modules @('ExchangeOnlineManagement', 'Microsoft.Graph', 'Microsoft.Entra')
```

The other parameters worth knowing: `-Scope` (`CurrentUser` by default, `AllUsers` needs elevation), `-AsciiArt` (the banner, on by default), `-RunInVSCode` (off by default) and `-KeepMultipleVersions` (new in 0.9.1).

## How It Works Inside

I read the module source from the Gallery to see what really happens at every shell start. Roughly, `Install-M365Module` does this:

1. **Exits in VS Code**, unless `-RunInVSCode` is set. The README says that is intentional.
2. **Prints the banner** when `-AsciiArt` is on.
3. **Checks elevation** on Windows. Without admin rights, `AllUsers` installs and removals are skipped with a warning.
4. **Trusts PSGallery.** If the repository is marked untrusted, the module warns and marks it trusted. Worth knowing if your hardening baseline cares about repository trust.
5. **Counts running `powershell`, `pwsh` and `code` processes.** More than one means a warning and a five-second countdown, because updating a module that another session has loaded is a bad idea.
6. **Checks PSResourceGet itself** and updates it if the Gallery has a newer version. If it finds several copies, it removes them all by deleting files and does not reinstall in that pass.
7. **Loops over the module list:**
   - not installed - installs the newest version
   - installed in several versions - after another five-second countdown deletes all of them and installs the newest (unless `-KeepMultipleVersions` is set)
   - installed in one version, and the Gallery has a newer one - deletes the old copy and installs the new one; for `Az`, `Microsoft.Graph` and `Microsoft.Graph.Beta` the related sub-modules are removed too
   - otherwise reports the module as up to date

There is no closing summary, only a status line per module. The old versions are removed by **file deletion**, not by `Uninstall-PSResource`; version 0.9.1 moved the uninstall command the same way (`Uninstall-M365Module -FileMode`). The reason is simple for anybody who ever fought with `Microsoft.Graph`: it is dozens of sub-modules, and a "normal" uninstall of a large module is slow and unreliable.

## The Other Commands

| Command | What it does |
|---|---|
| `Install-M365Module` | Installs or updates the modules (above) |
| `Uninstall-M365Module` | Removes the standard modules, or one module with `-Module`. `-FileMode` deletes the files directly |
| `Get-M365StandardModule` | Shows the standard list |
| `Add-M365PSProfile` | Adds the two profile lines |
| `Disconnect-All` | Closes the open remote PowerShell sessions and disconnects Teams and Graph; SharePoint Online, Exchange Online and PnP are disconnected only if their modules are loaded |
| `Set-WindowTitle` | Sets the console window title (default "Windows PowerShell"); supports `-WhatIf` |

In the code I read, `Disconnect-All` does not touch the other modules from the standard list (for example Entra), so it is not a full "sign out of everything" button, whatever the name suggests.

## Things to Watch For

- **It works at every shell start.** The authors say themselves that the check can add delay, and that you do not need to run it every time - you can call `Install-M365Module` manually instead. A profile line that checks 17 modules against the Gallery on a slow connection is something that gets noticed.

> **NEEDS YOUR LAB:** how long a new `pwsh` / `powershell` window takes with and without the profile line, on your normal connection and on the corporate proxy.

- **Always newest is not always what you want.** The module installs the latest version of each module. On a workstation used for production changes, a silent jump of `Microsoft.Graph` or `ExchangeOnlineManagement` to a new major version can change a script's behavior. That is my own concern, not something the authors claim; the answer may simply be to pin your own list with `-Modules`, or not to run the update from the profile at all.
- **OneDrive-redirected Documents.** The README lists a known problem: removal can fail on redirected OneDrive folders, because of a PSResourceGet bug. Since the profile and `CurrentUser` module folders live under Documents, a OneDrive-redirected profile is exactly the place where I would test first.
- **Files in use.** Removal by file deletion on Windows fails when another session has the module loaded; that is the reason for the countdown warning about other PowerShell processes.
- **Proxy and offline machines.** Everything comes from the PowerShell Gallery. A server without internet access, or with a restricted proxy, needs a different approach (internal repository, offline save).

## Why This Matters

For a lab or a personal admin workstation it is a very pleasant helper: one line in the profile, no admin rights, and a predictable set of modules after a fresh Windows install. For a team it is also a cheap way to get everybody to the same baseline, as long as the "latest version" policy is acceptable. The module is small enough to read in one evening, and I would read it before putting it into a shared profile - mostly for the repository trust change and the file-deletion logic.

## Closing Thought

> **NEEDS YOUR LAB:** your own verdict after using it - do you keep it in the profile or run `Install-M365Module` by hand, did the startup delay bother you, anything you changed in the module list (for example dropping `MSCommerce` or `WhiteboardAdmin`), and what to try next.

## References

- [M365PSProfile - PowerShell Gallery](https://www.powershellgallery.com/packages/M365PSProfile/) (release notes and version history)
- [M365PSProfile source - PowerShell Gallery (0.9.1 module file)](https://www.powershellgallery.com/packages/M365PSProfile/0.9.1/Content/M365PSProfile.psm1)
- [fabrisodotps1/M365PSProfile - GitHub](https://github.com/fabrisodotps1/M365PSProfile) (README, standard module list, license)
- [Keep your M365 PowerShell Modules up to date with M365PSProfile - Andres Bohren, icewolf.ch](https://blog.icewolf.ch/archive/2023/12/22/keep-your-m365-powershell-modules-up-to-date-with-m365psprofile/)
