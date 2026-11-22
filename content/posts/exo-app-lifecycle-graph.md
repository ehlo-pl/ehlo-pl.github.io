+++
title = 'The Lifecycle of an Exchange Online Application: From App Registration to Soft Delete'
date = '2026-11-22T12:00:00+01:00'
draft = true
description = "Registration, scoped permissions with RBAC for Applications, credentials, governance and decommissioning of apps that touch Exchange Online data"
tags = ["microsoft-graph", "exchange-online", "entra-id", "app-registration", "rbac-for-applications", "powershell"]
categories = ["Microsoft 365"]
+++

## The Discovery

Every Exchange Online tenant collects applications over time: a mail archiver, a room booking system, a reporting script running in Azure Automation, a "temporary" tool which somebody registered three years ago. Each of them talks to mailbox data through Microsoft Graph (or still EWS), and each of them has a life: somebody creates it, gives it permissions and a credential, and - if we are lucky - somebody removes it at the end.

> **NEEDS YOUR LAB:** one or two sentences on what triggered this post for you (an audit, an incident, a forgotten app with `Mail.Read` you found in a tenant).

I tried to put the whole lifecycle in one place, with the commands I would actually use for each stage.

## The Five Stages

```text
+-------------------+      +--------------------+      +--------------------+
| 1. Registration   | ---> | 2. Scoping &       | ---> | 3. Credential      |
|    (Entra ID)     |      |    Permissions     |      |    Management      |
+-------------------+      +--------------------+      +--------------------+
                                                                 |
    +-------------------+      +--------------------+            |
    | 5. Decommission   | <--- | 4. Monitoring &    | <----------+
    |    (Soft Delete)  |      |    Governance      |
    +-------------------+      +--------------------+
```

## 1. Registration and Tenant Provisioning

Two objects are created, and it is worth to keep them apart from the beginning:

- **Application object** (*App registrations* in Entra) - the definition: Application (client) ID, supported account types (single-tenant or multitenant), credentials, requested permissions.
- **Service principal** (*Enterprise applications*) - the instance of that application in a tenant. Every tenant where the app accesses resources has its own service principal, and that is the object which actually *holds* the permissions granted in the tenant.

For an internal Exchange automation, single-tenant is almost always the right answer. In Microsoft Graph PowerShell:

```powershell
Connect-MgGraph -Scopes 'Application.ReadWrite.All'

$app = New-MgApplication -DisplayName 'exo-mail-archiver' -SignInAudience 'AzureADMyOrg'
$sp  = New-MgServicePrincipal -AppId $app.AppId

$app.AppId   # client ID - used by the script
$sp.Id       # service principal object ID - needed later by Exchange
```

Keep both IDs. Exchange Online RBAC (next section) wants the **service principal** object ID, not the object ID from the App registrations page - Microsoft documentation explicitly warns that those are different values.

## 2. Permissions and Scoping

### The tenant-wide trap

Application permissions (app roles) let the app work without a signed-in user, and they need admin consent. The problem is their reach: an app with the Graph `Mail.Read` *application* permission consented in Entra can read **every mailbox in the organization**. For most real apps this is much more than needed.

### RBAC for Applications

The answer in Exchange Online is **RBAC for Applications**, which replaces the old Application Access Policies. Instead of consenting `Mail.Read` in Entra, you grant an Exchange *application role* (for example `Application Mail.Read`) to the service principal, together with a resource scope: a management scope (filter on mailbox properties) or an administrative unit.

```powershell
Connect-ExchangeOnline

# Pointer to the Entra service principal (AppId + service principal object ID)
New-ServicePrincipal -AppId $app.AppId -ObjectId $sp.Id -DisplayName 'exo-mail-archiver'

# Which mailboxes: here everything with CustomAttribute1 = 'archive'
New-ManagementScope -Name 'Archived mailboxes' -RecipientRestrictionFilter "CustomAttribute1 -eq 'archive'"

# What the app may do, limited to that scope
New-ManagementRoleAssignment -App $sp.Id -Role 'Application Mail.Read' -CustomResourceScope 'Archived mailboxes'

# Check the effective result against one mailbox
Test-ServicePrincipalAuthorization -Identity $sp.Id -Resource 'someone@contoso.com'
```

Instead of a management scope, `-RecipientAdministrativeUnitScope <AU id>` uses an Entra administrative unit directly.

> **NEEDS YOUR LAB:** `Test-ServicePrincipalAuthorization` output from your tenant - one mailbox in scope (`InScope = True`) and one outside.

Things which are easy to miss:

- **Permissions are a union.** If the app *also* has `Mail.Read` consented in Entra, the scoped Exchange grant restricts nothing - the unscoped Entra grant still applies. Remove the Entra consent when you move an app to RBAC for Applications.
- **Caching.** Changes take from 30 minutes up to 2 hours to apply to a running app. `Test-ServicePrincipalAuthorization` bypasses that cache, so a green test does not mean the app already sees the change.
- **Exclusive management scopes don't restrict app access**, and apps can't be members of role groups.
- Supported protocols are Microsoft Graph and EWS. Autodiscover can't be used with RBAC application roles.

### Managing Exchange itself (not only mailbox data)

A different case is an unattended script which runs Exchange cmdlets (`Connect-ExchangeOnline` with a certificate). Here the app needs the **Office 365 Exchange Online > `Exchange.ManageAsApp`** application permission, plus RBAC: either a Microsoft Entra role assigned to the app (Exchange Recipient Administrator, Global Reader, Exchange Administrator...) or - better for least privilege - the service principal added to a custom Exchange role group.

## 3. Credentials

An app authenticates with a client secret, a certificate, or a federated identity credential (workload identity federation, managed identities).

- **Prefer certificates over secrets** in production. For unattended jobs like Azure Automation runbooks a certificate is the standard way, and Exchange Online PowerShell app-only authentication is built around certificates anyway. One Exchange-specific gotcha: CNG certificates aren't supported for app-only authentication with Exchange - the key must come from a CSP provider.
- **Expiration is a feature, plan for it.** Client secrets created in the portal live at most two years. When a certificate expires, a new one has to be uploaded to the app *and* the scripts must be switched to the new thumbprint - otherwise authentication simply stops.
- **Store credentials in Azure Key Vault**, not in the script or on a jump host.

A quick report of credentials expiring in the next 60 days:

```powershell
Connect-MgGraph -Scopes 'Application.Read.All'

$limit = (Get-Date).AddDays(60)
Get-MgApplication -All -Property DisplayName, AppId, PasswordCredentials, KeyCredentials |
    ForEach-Object {
        $a = $_
        $a.PasswordCredentials | Select-Object @{n='App';e={$a.DisplayName}}, @{n='Type';e={'Secret'}}, EndDateTime
        $a.KeyCredentials      | Select-Object @{n='App';e={$a.DisplayName}}, @{n='Type';e={'Certificate'}}, EndDateTime
    } |
    Where-Object { $_.EndDateTime -and $_.EndDateTime -lt $limit } |
    Sort-Object EndDateTime
```

> **NEEDS YOUR LAB:** sample output of the expiry report (anonymized app names are fine).

## 4. Monitoring and Governance

An app which works is not finished - its permissions only grow if nobody looks.

- **Review permission assignments regularly**: are they still appropriate, still needed? Microsoft Graph PowerShell lets you pull consent and app role assignments per service principal and build a simple warning process on top.
- **Application management policies** put guard rails on app registrations for the whole tenant: block new client secrets, limit secret and certificate lifetime, allow only trusted certificate authorities. The tenant-wide default policy is changed with `Update-MgPolicyDefaultAppManagementPolicy` (Graph: `PATCH /policies/defaultAppManagementPolicy`). A `restrictForAppsCreatedAfterDateTime` value lets you apply it to new apps first and leave the old ones alone until they are cleaned up.

> **Note:** with a lifetime restriction in place, uploading a certificate which lives longer than allowed fails with *"Credential lifetime exceeds the max value allowed as per assigned policy"*. Worth to know before the next certificate rollover.

## 5. Deactivation, Deletion and Recovery

### Deactivate first

Entra ID can now **deactivate** an app registration instead of deleting it. A deactivated app gets no new access tokens and can't access protected resources, but its configuration, permissions and service principal stay in place - so reactivation is immediate. Existing tokens stay valid until they expire, so it is not an instant kill switch.

```powershell
Connect-MgGraph -Scopes 'Application.ReadWrite.All'

# Deactivate (beta endpoint at the time of writing)
Invoke-MgGraphRequest -Method PATCH `
    -Uri "https://graph.microsoft.com/beta/applications(appId='$($app.AppId)')" `
    -Body @{ isDisabled = $true }

# List all deactivated apps
Invoke-MgGraphRequest -Method GET `
    -Uri 'https://graph.microsoft.com/beta/applications?$filter=isDisabled eq true'
```

It needs at least the Cloud Application Administrator (or Application Administrator) role. Remove other owners before you deactivate, otherwise an owner can simply reactivate the app. Each change is logged in the Entra audit log as *Update application* with the `isDisabled` property.

Do not confuse it with **disabling sign-in** on the service principal (`accountEnabled = false`): that works only in one tenant, while deactivation is global for the app.

### Delete

When the app is really not needed any more, delete the application object. Deleting an app registration removes its service principal in the home tenant too, and in Exchange Online the service principal pointer and its role assignments disappear automatically (management scopes stay, clean them up yourself).

### Restore within 30 days

Deleted applications sit in the recycle bin for 30 days, and can be restored with their original object ID:

```powershell
Connect-MgGraph -Scopes 'Application.ReadWrite.All'

Get-MgDirectoryDeletedItemAsApplication -All | Select-Object DisplayName, Id, DeletedDateTime
Restore-MgDirectoryDeletedItem -DirectoryObjectId '<application object ID>'
```

One surprise: **restoring an application does not restore its service principal**. The service principal has to be restored explicitly with the same cmdlet - and Exchange role assignments, which were removed with it, have to be recreated.

## Why This Matters

Exchange admins spent years tuning RBAC for *people*: role groups, scopes, split permissions. Applications got much less attention, while one app with tenant-wide `Mail.Read` reads more than any helpdesk operator. The pieces for doing it properly are there now - scoped app roles in Exchange, policies for credentials, reversible deactivation - but they live in two consoles (Entra and Exchange) and the effective permission is the union of both. That is exactly the place where mistakes hide.

## Closing Thought

> **NEEDS YOUR LAB:** your own conclusion - for example which stage you see most often neglected in real tenants, and whether you would move existing apps from Application Access Policies to RBAC for Applications now.

## References

- [Application and service principal objects in Microsoft Entra ID](https://learn.microsoft.com/entra/identity-platform/app-objects-and-service-principals)
- [Role Based Access Control for Applications in Exchange Online](https://learn.microsoft.com/exchange/permissions-exo/application-rbac)
- [App-only authentication for unattended scripts in Exchange Online PowerShell](https://learn.microsoft.com/powershell/exchange/app-only-auth-powershell-v2)
- [Grant tenant-wide admin consent to an application](https://learn.microsoft.com/entra/identity/enterprise-apps/grant-admin-consent)
- [Configure restrictions on how applications can be configured (app management policies)](https://learn.microsoft.com/entra/identity/enterprise-apps/configure-app-management-policies)
- [Tutorial: Enforce secret and certificate standards using application management policies](https://learn.microsoft.com/entra/identity/enterprise-apps/tutorial-enforce-secret-standards)
- [Deactivate an app registration](https://learn.microsoft.com/entra/identity/enterprise-apps/deactivate-app-registration)
- [Restore-MgDirectoryDeletedItem](https://learn.microsoft.com/powershell/module/microsoft.graph.identity.directorymanagement/restore-mgdirectorydeleteditem)
- *Automating Microsoft 365 with PowerShell* (2027 edition) - book
