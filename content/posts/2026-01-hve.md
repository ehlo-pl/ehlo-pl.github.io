+++
title = "HVE"
date = 2026-01-01T00:00:00Z
draft = true
description = "Untitled"
+++



Work on entra 



```powershell
S /home/zblab> history| select -ExpandProperty commandline | ft -a -Wrap
# Connect to Exchange Online
Connect-ExchangeOnline
# --- Variables ---
$tenantid  = '68057f34-a627-4a49-b61b-61bc9375549f'
$AppId  = '444747c6-93fd-4967-8c94-69507568099f'          # From Enterprise App
$ObjectId  = "ce2d9cfd-c8c7-4125-bfc1-f9fdb5e6173f"             # From Enterprise App (NOT App Registration!)
$DisplayName = "HVE Mail Sender App"
# --- Create Service Principal in Exchange Online ---
New-ServicePrincipal -AppId $AppId -ObjectId $ObjectId -DisplayName $DisplayName
# Verify
Get-ServicePrincipal | Where-Object { $_.AppId -eq $AppId } | Format-List
# Option A: Scope to specific HVE account(s)
New-ManagementScope -Name "HVE-Senders-Scope"  -RecipientRestrictionFilter "Alias -eq 'hvetesting' -or Alias -eq 'hvetest2'" -WhatIf
New-ManagementScope -Name "HVE-Senders-Scope"  -RecipientRestrictionFilter "Alias -eq 'hvetesting' -or Alias -eq 'hvetest2'" 
New-ManagementRoleAssignment -App $AppId  -Role "Application Mail.Send"     -CustomResourceScope "HVE-Senders-Scope"
Test-ServicePrincipalAuthorization -Identity $AppId
Test-ServicePrincipalAuthorization -Identity $AppId -resource hvetesting@zblab2021.eu
history
```

```python

```