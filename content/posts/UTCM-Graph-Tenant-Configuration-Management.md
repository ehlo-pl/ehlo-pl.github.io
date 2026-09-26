+++
title = 'Microsoft Graph Unified Tenant Configuration Management (UTCM): Snapshots, Monitors and Drift'
date = '2026-09-26T10:00:00+02:00'
draft = true
description = "First look at Microsoft Graph Tenant Configuration Management APIs (UTCM): snapshots, configurationMonitors and configuration drift across Exchange Online, Entra, Teams, Intune and more"
tags = ["microsoft-graph", "utcm", "tcm", "microsoft-365", "exchange-online", "entra-id", "powershell", "configuration-drift"]
categories = ["PowerShell"]
+++

## The Discovery

I noticed a new endpoint in Microsoft Graph that I had not seen before:

```
https://graph.microsoft.com/v1.0/admin/configurationManagement/configurationMonitors
```

`admin/configurationManagement` — this sounds like something every Microsoft 365 admin was waiting for. Anybody who ever tried to answer the question "who changed this transport rule (or Conditional Access policy) and when?" knows the pain. Until now the answer was: audit logs, some homemade script, or a third-party tool.

This is **Unified Tenant Configuration Management** (UTCM), sometimes just called TCM in Microsoft documents. This post is my notes from reading what is available: Microsoft Learn, a few community articles, and two PowerShell modules from the gallery.

## What Is UTCM?

Tenant Configuration Management is a set of Graph APIs for configuration-as-code in Microsoft 365. Office365ITPros describes it as a Microsoft-engineered version of Desired State Configuration (DSC) — same idea, different technology underneath. You describe how the tenant should look, and the service tells you when reality is different.

Workloads covered (according to the community articles at the time of preview): Exchange Online, Entra, Purview, Teams, Intune and Defender (limited). SharePoint Online and OneDrive are not covered. Microsoft says the solution supports hundreds of resource types (over 300 was mentioned), for example `microsoft.entra.conditionalaccesspolicy` or `microsoft.exchange.transportrule`.

It is not available in government or China clouds — Microsoft Learn shows the global service only.

A word about the status: early articles from January/February 2026 talk about public preview and `/beta/` endpoints. Microsoft Learn now documents the same APIs under `v1.0` and Entra Tenant Governance docs call them generally available. However, the authentication article still says "during public preview" when describing service principal setup. So the state is a bit blurry; check the docs before you rely on it.

## The Building Blocks

Four objects to remember:

| Object | What it is |
| --- | --- |
| **Snapshot** (`configurationSnapshotJob`) | Extracts the current configuration of chosen resource types. Asynchronous job. |
| **Baseline** (`configurationBaseline`) | JSON list of resources and property values expected in the tenant. |
| **Monitor** (`configurationMonitor`) | Runs periodically, compares tenant with the baseline. |
| **Drift** (`configurationDrift`) | A difference found by the monitor: which resource, which property, current vs. desired value. |

Each monitor run also produces a **monitoring result** (`configurationMonitoringResult`) — a summary with status, duration and count of drifts. It does not include details, for these you need to query drifts.

Typical flow: take a snapshot of a configuration you consider good → turn it into a baseline → create a monitor with that baseline → wait for drifts.

## How It Works

### Two levels of authentication

This part confused me at first. Microsoft documents two separate things:

1. **You authenticate to Graph** to manage monitors or start snapshots. For a user that means any privileged Entra role (custom roles are not supported, per the community article). For an app, it is `ConfigurationMonitoring.Read.All` or `ConfigurationMonitoring.ReadWrite.All` (snapshots need ReadWrite).
2. **The monitor itself** runs as a Microsoft service principal called **Tenant Configuration Management** with appId `03b07b79-c5bc-4b5e-9bfa-13acf4a99998`. This principal must exist in your tenant, and it needs read permissions to whatever the baseline is checking. Otherwise the job fails or ends as `partiallySuccessful` (I read about `Access Denied. Provide different credential or request access.` in one article).

Microsoft also notes that the **M365 Admin Services** service principal (appId `6b91db1b-f05b-405a-a0b2-e3f60b28d645`) should be provisioned in the tenant.

### Create the service principal

From Microsoft Learn:

```powershell
Install-Module Microsoft.Graph.Authentication
Install-Module Microsoft.Graph.Applications
Connect-MgGraph -Scopes @('Application.ReadWrite.All', 'AppRoleAssignment.ReadWrite.All')

New-MgServicePrincipal -AppId '03b07b79-c5bc-4b5e-9bfa-13acf4a99998'
```

Then grant it Graph application permissions. The documentation example uses `User.ReadWrite.All` and `Policy.Read.All`; which permissions you really need depends on the resources in your baseline. For Conditional Access I would start with `Policy.Read.All`.

```powershell
$permissions = @('Policy.Read.All')
$Graph = Get-MgServicePrincipal -Filter "AppId eq '00000003-0000-0000-c000-000000000000'"
$TCM   = Get-MgServicePrincipal -Filter "AppId eq '03b07b79-c5bc-4b5e-9bfa-13acf4a99998'"

foreach ($requestedPermission in $permissions) {
    $AppRole = $Graph.AppRoles | Where-Object { $_.Value -eq $requestedPermission }
    $body = @{
        AppRoleId   = $AppRole.Id
        ResourceId  = $Graph.Id
        PrincipalId = $TCM.Id
    }
    New-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $TCM.Id -BodyParameter $body
}
```

For Exchange Online monitoring it is more work: the service principal needs `Exchange.ManageAsApp` plus an Exchange or Entra role (Nik Charlebois mentions Security Reader and Teams Reader for the Teams/Exchange resources in his example). Microsoft points to the [application RBAC for Exchange Online](https://learn.microsoft.com/en-us/exchange/permissions-exo/application-rbac) article.

Nik also mentions a helper module `TCM.Utility` that analyzes a template and lists the minimal permissions required. I did not test it.

### Snapshot

A snapshot is an asynchronous job. The body of the POST is the list of resource types to extract:

```powershell
Connect-MgGraph -Scopes 'ConfigurationMonitoring.ReadWrite.All'

$body = @{
    displayName = "Conditional Access Baseline"
    description = "Critical CA policies"
    resources   = @(
        "microsoft.entra.conditionalaccesspolicy"
    )
}
Invoke-MgGraphRequest -Method POST `
    -Uri "beta/admin/configurationManagement/configurationSnapshots/createSnapshot" `
    -Body $body
```

(the community articles use `beta` here — check the v1.0 reference for the current path.)

Then poll `configurationSnapshotJobs`. When the job finishes, it contains `resourceLocation` — a URL where the extracted configuration lives:

```powershell
$filter   = "displayName eq 'Conditional Access Baseline'"
$job      = (Invoke-MgGraphRequest -Method GET -OutputType PSObject `
             -Uri "beta/admin/configurationManagement/configurationSnapshotJobs/?`$filter=$filter").value
$snapshot = Invoke-MgGraphRequest -Method GET -Uri $job[0].resourceLocation
```

Things to know about snapshots (from Microsoft Learn limits):

- snapshot is retained for max **7 days** — it is not a backup storage, save the JSON yourself
- max **20,000 resources** extracted per tenant per month (cumulative)
- max **12 snapshot jobs** visible at once; delete old ones to create new
- the IaC-UTCM repo notes also that a single snapshot job cannot mix Entra and Intune resources, and display names accept only alphanumeric characters and spaces

### Monitor

Now the endpoint from the title. A monitor is created by POSTing `displayName`, optional `description`, and a `baseline` with at least one resource and one property. Example based on the Microsoft Learn sample (Exchange Online):

```json
POST https://graph.microsoft.com/v1.0/admin/configurationManagement/configurationMonitors
Content-Type: application/json

{
  "displayName": "Demo Monitor",
  "description": "This is a Demo Monitor",
  "baseline": {
    "displayName": "Demo Baseline",
    "description": "Accepted domain check",
    "resources": [
      {
        "displayName": "Accepted Domain",
        "resourceType": "microsoft.exchange.accepteddomain",
        "properties": {
          "Identity": "contoso.onmicrosoft.com",
          "DomainType": "InternalRelay",
          "Ensure": "Present"
        }
      }
    ]
  }
}
```

The response is `201 Created`, and the monitor comes with `status: active`, `monitorRunFrequencyInHours: 6` and `mode: monitorOnly`.

If you use the snapshot as a baseline, the flow from the OurCloudNetwork article is to take the snapshot content and pass `displayName`, `resourceType` and `properties` of every resource into the baseline:

```powershell
$body = @{
    displayName = "Conditional Access Monitor"
    description = "Critical CA policies Monitor"
    baseline    = @{
        displayName = $snapshot.displayName
        description = $snapshot.description
        resources   = ($snapshot.resources | Select-Object displayName, resourceType, properties)
    }
} | ConvertTo-Json -Depth 10

Invoke-MgGraphRequest -Method POST -Body $body `
    -Uri "beta/admin/configurationManagement/configurationMonitors"
```

Note `-Depth 10` — without it `ConvertTo-Json` flattens nested properties and you get a broken baseline.

Limits worth knowing:

- max **30 monitors** per tenant
- fixed interval **every 6 hours** — cannot be changed
- max **800 monitored resources per day per tenant**. A resource in a baseline is checked 4 times a day, so it costs 4 units. Microsoft example: 20 transport rules + 30 CA policies = 50 resources × 4 = 200 per day. Simple math: about 200 resources in total across all monitors is the real ceiling
- when you update a monitor baseline, all previous monitoring results and drifts for that monitor **are deleted**

### Results and drift

```powershell
$monitor = (Invoke-MgGraphRequest -Method GET -OutputType PSObject `
    -Uri "beta/admin/configurationManagement/configurationMonitors/?`$filter=displayName eq 'Conditional Access Monitor'").value

# summary of every run
Invoke-MgGraphRequest -Method GET -OutputType PSObject `
    -Uri "beta/admin/configurationManagement/configurationMonitoringResults?`$filter=monitorId eq '$($monitor[0].id)'"

# details of drifts
Invoke-MgGraphRequest -Method GET -OutputType PSObject `
    -Uri "beta/admin/configurationManagement/configurationDrifts?`$filter=monitorId eq '$($monitor[0].id)'"
```

A drift object has `resourceType`, `baselineResourceDisplayName`, `firstReportedDateTime`, `status` (`active` or `fixed`) and `driftedProperties` (with the current and desired value). Note that `driftedProperties` and `resourceInstanceIdentifier` are returned only when you ask for them with `$select`.

There is no "revert" button. In the current monitor mode (`monitorOnly`) the service only reports. You either fix the setting yourself in the admin center (next run marks the drift as `fixed`, and it is deleted 30 days later), or you accept the change and create a new baseline. Microsoft mentions a more sophisticated resolution mechanism in the future.

> **NEEDS YOUR LAB:** real output from my tenant: `createSnapshot` response, the finished snapshot job with `resourceLocation`, one monitoring result and one drift after I change a Conditional Access policy or transport rule. Screenshot or JSON captured after the first 6-hour cycle.

## Tooling Around It

Because the raw REST calls are quite verbose, community modules already appeared on the PowerShell Gallery:

- **UTCM** (Jan Ketil Skanke) — 21 functions, PowerShell 7+, no Graph SDK dependency. Covers connection (`Connect-UTCM`), monitors (`New-UTCMMonitor`, `Get-UTCMDrift`), snapshots (`New-UTCMSnapshot`, `Wait-UTCMSnapshot`, `Compare-UTCMSnapshot`) and permission setup (`Install-UTCMServicePrincipal`, `Grant-UTCMPermission`).
- **EasyTCM** (Loic Michel, EasyPIM approach) — 23 functions like `New-TCMSnapshot`, `ConvertTo-TCMBaseline`, `New-TCMMonitor`, `Get-TCMDrift`, `Export-TCMDriftReport`, `Get-TCMQuota`, and `Sync-TCMDriftToMaester` for integration with the Maester testing framework.
- **IaC-UTCM** on GitHub (ElliottLW) — a set of numbered PowerShell scripts (setup, connect, snapshot, monitor, teardown) which puts UTCM snapshots next to Bicep or Terraform. The author validated 13 resource types (9 Entra, 4 Intune).

I did not install any of them yet, so no opinion about quality.

> **NEEDS YOUR LAB:** short test of one of the modules (UTCM or EasyTCM) — install, connect, one snapshot — and what I think about it compared with raw `Invoke-MgGraphRequest`.

## Why This Matters

- Native drift detection for tenant configuration, without buying a separate product. For Exchange Online it covers things I care about: transport rules, accepted domains, mail contacts, shared mailboxes.
- The baseline is JSON, so it can live in Git and go through a pull request like any other code.
- The API is plain Graph, so SDKs (PowerShell `Microsoft.Graph.ConfigurationManagement`, C#, Go, Python...) are available.

And what stops me:

- 6 hours fixed frequency — this is drift detection, not real-time alerting
- 800 resources per day quota is small for a big tenant
- monitors only report; no remediation yet
- there is a permission puzzle — a service principal that reads your whole tenant configuration must be handled with care (least privilege, and remember that monitors run as the UTCM principal regardless of who created them)
- 7 days snapshot retention forces you to store the JSON elsewhere

## Closing Thought

I like the direction. Mail-flow configuration is exactly the kind of thing that changes quietly and breaks something a week later — and now there is an official API to ask "what is different from yesterday". Next step for me: build a small baseline for transport rules and accepted domains in the lab tenant, and see how noisy the drifts are. Probably a Go or PowerShell tool on top of it, if the modules above do not already do what I want.

> **NEEDS YOUR LAB:** one or two sentences about the YouTube video "Microsoft Entra Tenant Governance | Find Configuration Drift" (listed in references) — what it showed, in your own words. I could not read its content.

## References

- [Use the Tenant Configuration Management APIs in Microsoft Graph](https://learn.microsoft.com/en-us/graph/unified-tenant-configuration-management-concept-overview)
- [Set up authentication for Tenant Configuration Management APIs](https://learn.microsoft.com/en-us/graph/utcm-authentication-setup)
- [Create configurationMonitor](https://learn.microsoft.com/en-us/graph/api/configurationmanagement-post-configurationmonitors?view=graph-rest-1.0)
- [configurationDrift resource type](https://learn.microsoft.com/en-us/graph/api/resources/configurationdrift?view=graph-rest-1.0)
- [Configuration management (Entra Tenant Governance)](https://learn.microsoft.com/en-us/entra/id-governance/tenant-governance/configuration-management)
- [Office365ITPros: Unified Tenant Configuration Management (UTCM) beta](https://office365itpros.com/2026/02/03/utcm-beta/)
- [Nik Charlebois: Introducing the TCM APIs](https://nik-charlebois.com/blog/posts/2026/introducing-tcm-apis/index.html)
- [OurCloudNetwork: How to set up Unified Tenant Configuration Management](https://ourcloudnetwork.com/how-to-setup-unified-tenant-configuration-management/)
- [YouTube: Microsoft Entra Tenant Governance | Find Configuration Drift](https://www.youtube.com/watch?v=nIOantcKcOI)
- [ElliottLW/IaC-UTCM on GitHub](https://github.com/ElliottLW/IaC-UTCM)
- [EasyTCM 0.5.0 on PowerShell Gallery](https://www.powershellgallery.com/packages/EasyTCM/0.5.0)
- [UTCM 0.1.1 on PowerShell Gallery](https://www.powershellgallery.com/packages/UTCM/0.1.1)
