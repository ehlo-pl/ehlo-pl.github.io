+++
title = "Notes from the Field: Managing User Photos in Exchange Online"
date = 2023-03-01T00:00:00Z
draft = true
description = "Where Microsoft 365 user photos live now, which Graph cmdlets replaced Set-UserPhoto, shared mailboxes and Microsoft 365 Groups, the 10 KB hybrid trap, and who is allowed to change a photo"
tags = ["m365", "powershell", "exo", "microsoft-graph", "entra-id", "shared-mailbox", "m365-groups"]
categories = ["Microsoft 365"]
+++

## The Ticket Nobody Wants

"My photo in Outlook is still the old one." "Teams shows a different picture than the address book." "HR wants all photos replaced before the new intranet goes live."

User photos look like the most boring part of a messaging platform. In practice they come back every few months, and each time the answer is a bit different, because Microsoft moved the photo around between Active Directory, the Exchange mailbox and Entra ID. These are my notes, so next time I don't start from a search engine and a pile of 2016 blog posts.

## Where the Photo Lives

There are three places worth knowing:

- **On-premises Active Directory** – the `thumbnailPhoto` attribute. Still used by on-premises Exchange, the old GAL and many HR or badge systems.
- **The Exchange mailbox** – for years Exchange Online kept the high-resolution photo in the mailbox, and `Set-UserPhoto` wrote it there. That is history for the cloud.
- **Microsoft Entra ID** – today the source of truth for Microsoft 365. Outlook, Teams, SharePoint and the rest read the photo through Microsoft Graph.

The important consequence: in Microsoft 365 you manage photos with **Microsoft Graph**, not with Exchange Online PowerShell.

## Old Toolbox vs New Toolbox

Microsoft announced the retirement of the Exchange Online `UserPhoto` cmdlets in October 2023 (Message Center MC678855), and they stopped working for tenant admins in 2024. They still work in Exchange Server on-premises. The AzureAD and MSOnline PowerShell modules are retired too, and EWS in Exchange Online is on its way out, so none of the old routes is a good choice for new scripts.

| Task | Old way | Now (Microsoft Graph PowerShell) |
|---|---|---|
| Upload a photo | `Set-UserPhoto` (EXO) | `Set-MgUserPhotoContent -UserId <upn> -InFile <file>` |
| Photo metadata (size) | `Get-UserPhoto` (EXO) | `Get-MgUserPhoto -UserId <upn>` |
| Download a photo | `Get-UserPhoto` / `Get-AzureADUserThumbnailPhoto` / EWS `GetUserPhoto` | `Get-MgUserPhotoContent -UserId <upn> -OutFile <file>` |
| Remove a photo | `Remove-UserPhoto` (EXO) | `Remove-MgUserPhoto -UserId <upn>` |
| REST | EWS / Outlook REST | `GET/PUT/DELETE /users/{id}/photo/$value` |

JPEG and PNG files up to 4 MB are accepted. The Microsoft 365 admin center can upload a photo too, but it can't remove one – removing needs Graph.

## Everyday Commands

Single user:

```powershell
Connect-MgGraph -Scopes 'ProfilePhoto.ReadWrite.All' -NoWelcome

Set-MgUserPhotoContent -UserId 'anna@contoso.com' -InFile 'C:\Photos\anna.jpg'
Get-MgUserPhoto        -UserId 'anna@contoso.com'          # Height / Width
Get-MgUserPhotoContent -UserId 'anna@contoso.com' -OutFile 'C:\Temp\anna.jpg'
Remove-MgUserPhoto     -UserId 'anna@contoso.com'
```

If the user has no photo, `Get-MgUserPhoto` throws an `ImageNotFoundException` – handle it in scripts instead of treating it as a failure.

Export all photos of enabled users (useful before a mass replacement – keep the old set):

```powershell
Connect-MgGraph -Scopes 'User.Read.All' -NoWelcome
$out = 'C:\Temp\PhotoBackup'
New-Item -ItemType Directory -Path $out -Force | Out-Null

Get-MgUser -All -Filter 'accountEnabled eq true' -Property Id, UserPrincipalName |
  ForEach-Object {
    $u = $_
    try {
      Get-MgUserPhotoContent -UserId $u.Id -OutFile (Join-Path $out "$($u.UserPrincipalName).jpg") -ErrorAction Stop
    } catch {
      Write-Verbose "No photo for $($u.UserPrincipalName)"
    }
  }
```

Import from a folder where each file is named `<UPN>.jpg`:

```powershell
Connect-MgGraph -Scopes 'ProfilePhoto.ReadWrite.All' -NoWelcome

Get-ChildItem 'C:\Temp\NewPhotos' -Filter *.jpg | ForEach-Object {
  $upn = $_.BaseName
  if ($_.Length -gt 4MB) { Write-Warning "${upn}: file is over 4 MB, skipped"; return }
  Set-MgUserPhotoContent -UserId $upn -InFile $_.FullName
}
```

For an unattended job use an app registration with the **application** permission `ProfilePhoto.ReadWrite.All` – it is the least privileged permission for updating other users' photos. `User.ReadWrite.All` works as well, but gives the app much more than it needs.

## Shared Mailboxes and Microsoft 365 Groups

Two cases come up all the time, and they behave differently: the **shared mailbox** (the shared "info@" or "helpdesk@" box) and the **Microsoft 365 Group** (the mailbox behind a Team, a Viva Engage community or a Planner plan). They sound alike, and they are different objects in Entra ID.

### Shared mailboxes

A shared mailbox is a user object in Entra ID that nobody is supposed to sign in to. Microsoft says its account should always have [sign-in blocked](https://learn.microsoft.com/microsoft-365/admin/email/about-shared-mailboxes). Two consequences:

- **The user commands apply.** Use `Set-MgUserPhotoContent`, `Get-MgUserPhoto`, `Get-MgUserPhotoContent` and `Remove-MgUserPhoto` with the shared mailbox UPN or object ID. A report on the Graph SDK issue tracker shows the same call working on a regular and on a shared mailbox.
- **Nobody can do it from the "my photo" page.** Without sign-in there is no self-service. The "change photo" link in Outlook on the web sends a delegate to *their own* photo. It has to be an admin, or a script running as an app.

```powershell
Connect-MgGraph -Scopes 'ProfilePhoto.ReadWrite.All' -NoWelcome

$sm = 'helpdesk@contoso.com'
Set-MgUserPhotoContent -UserId $sm -InFile 'C:\Photos\helpdesk.png'
Get-MgUserPhoto        -UserId $sm
```

Things to know:

- **There is no Exchange shortcut anymore.** `Set-UserPhoto <shared mailbox>` used to do this, and it is retired like the rest. Do not look for a `-SharedMailbox` switch – the Graph replacement table in the Exchange Team's retirement post lists user and group mailboxes only, and says nothing about shared ones.
- **Find shared mailboxes by their object ID.** `Get-EXOMailbox -RecipientTypeDetails SharedMailbox` returns `ExternalDirectoryObjectId`, which you can feed straight into `-UserId`. That helps in bulk jobs where display names are not unique.
- **A hybrid shared mailbox follows the hybrid rules.** If the account is synced from on-premises AD, the 10 KB limit from the previous section is the first suspect when a photo does not appear. Setting the photo in the cloud is the safe route.
- **Not every mailbox behaves like a regular one.** A bug report on the SDK tracker describes `Set-MgUserPhotoContent` failing with an internal store error on a Microsoft Bookings mailbox while working on a regular and a shared mailbox. It is an old report; test before you rely on it.
- **Distribution lists and mail contacts have no photo this way.** The old `Set-UserPhoto` could not set them either, and Graph's `contact` photo is a different thing (an Outlook contact in someone's mailbox).

> **NEEDS YOUR LAB:** run the commands above on a real shared mailbox (sign-in blocked) and note the result: does `Set-MgUserPhotoContent` succeed, does `Get-MgUserPhoto` return the new size, and where does the photo actually appear (Outlook desktop, Outlook on the web, Teams, address book, the From line)? A screenshot or two would carry this section.

### Microsoft 365 Groups

A group has its own photo, stored on the group object, and the group cmdlets are separate from the user ones:

```powershell
Connect-MgGraph -Scopes 'Group.ReadWrite.All' -NoWelcome

$g = Get-MgGroup -Filter "displayName eq 'Sales Department'"
Set-MgGroupPhotoContent -GroupId $g.Id -InFile 'C:\Photos\sales.png'
Get-MgGroupPhoto        -GroupId $g.Id
Get-MgGroupPhotoContent -GroupId $g.Id -OutFile 'C:\Temp\sales.png'
Remove-MgGroupPhoto     -GroupId $g.Id
```

What differs from users:

- **Identifier.** The group cmdlets take only the object ID (GUID). The user cmdlets accept an object ID, an SMTP address or a UPN. Do the `Get-MgGroup` lookup first.
- **Old equivalent.** This replaces `Set-UserPhoto -GroupMailbox`, which was the only Exchange route for groups.
- **Permissions.** Microsoft's mapping table lists `Group.ReadWrite` for a group owner and `Group.ReadWrite.All` for everyone else. The Graph reference lists `ProfilePhoto.ReadWrite.All` as the least privileged option for groups, delegated and application.
- **No admin center.** The Microsoft 365 admin center manages user photos, not group photos. Groups are Graph PowerShell only.
- **Application-only is uncertain.** The current Graph reference lists application permissions for groups, but I also found wording elsewhere that an app with only application permissions cannot update a group's photo. If you automate it with an app registration, test it.
- **Teams use their own endpoint.** A team's photo goes through the team's photo API (`TeamSettings.ReadWrite.All`), not the group one – there is a `Set-MgTeamPhotoContent` cmdlet.

| Object | Cmdlet to set the photo | Identifier | Admin center |
|---|---|---|---|
| User | `Set-MgUserPhotoContent` | OID, SMTP or UPN | yes (cannot remove) |
| Shared mailbox | `Set-MgUserPhotoContent` | OID, SMTP or UPN | not documented, Entra admin center per a Q&A answer |
| Microsoft 365 Group | `Set-MgGroupPhotoContent` | OID only | no |
| Team | `Set-MgTeamPhotoContent` | team ID | no (Teams client or Graph) |

## The Hybrid Trap: 100 KB vs 10 KB

The classic hybrid case: HR updates `thumbnailPhoto` in on-premises AD, Entra Connect syncs it, and Outlook and Teams keep showing the old picture.

The reason is two different size limits. `thumbnailPhoto` holds up to 100 KB, and it syncs to Entra ID, but Exchange Online picks up a photo from Entra ID only if it is at most **10 KB**. Anything between 10 and 100 KB syncs and then quietly goes nowhere. Microsoft's fix is to set the photo directly in the cloud (admin center or Graph), where the 4 MB limit applies.

Finding the candidates on-premises:

```powershell
Get-ADUser -Filter * -Properties thumbnailPhoto |
  Where-Object { $_.thumbnailPhoto.Length -gt 10KB } |
  Select-Object SamAccountName, @{ n = 'KB'; e = { [math]::Round($_.thumbnailPhoto.Length / 1KB, 1) } }
```

My preference: keep a small (under 10 KB) `thumbnailPhoto` for on-premises consumers, and push the proper photo to the cloud with Graph from the same HR source.

## Who Is Allowed to Change a Photo

By default every user can change their own photo, which is not always what HR or corporate communications want. Since 2024 there is a tenant-wide **photo update settings** policy in Graph (beta at the time of writing). It controls where photos may be updated from (`cloud` or `onPremises`) and which admin roles may update them (`allowedRoles`, a list of Entra role template IDs; empty means no restriction). Managing it needs `PeopleSettings.ReadWrite.All`.

```powershell
Connect-MgGraph -Scopes 'PeopleSettings.ReadWrite.All' -NoWelcome
$uri = 'https://graph.microsoft.com/beta/admin/people/photoUpdateSettings'

Invoke-MgGraphRequest -Method GET -Uri $uri

# Only Global Administrator and User Administrator may update photos
$body = @{
  source       = 'cloud'
  allowedRoles = @('62e90394-69f5-4237-9190-012177145e10',  # Global Administrator
                   'fe930be7-5e62-47db-91af-98c3a49a38b1')  # User Administrator
} | ConvertTo-Json
Invoke-MgGraphRequest -Method PATCH -Uri $uri -Body $body -ContentType 'application/json'
```

Test it in a lab tenant first – it is a beta API and it changes the experience for every user at once.

## Closing Thought

The photo finally has one home in Microsoft 365, and that is good news. The cost is the usual one: one-line Exchange cmdlets replaced by Graph, with scopes, consent and app registrations around them. For a one-off fix the admin center is enough; for anything repeatable – onboarding, HR feeds, mass refresh – write it once against Graph and stop touching `Set-UserPhoto` muscle memory.

## References

- [Deprecation of Exchange Online PowerShell UserPhoto cmdlets – Exchange Team Blog](https://techcommunity.microsoft.com/blog/exchange/deprecation-of-exchange-online-powershell-userphoto-cmdlets/3955744)
- [Change user profile photos – Microsoft 365 admin](https://learn.microsoft.com/microsoft-365/admin/add-users/change-user-profile-photos)
- [Update profilePhoto – Microsoft Graph](https://learn.microsoft.com/graph/api/profilephoto-update)
- [Delete profilePhoto – Microsoft Graph](https://learn.microsoft.com/graph/api/profilephoto-delete)
- [Manage user profile photo settings with Microsoft Graph](https://learn.microsoft.com/graph/profilephoto-configure-settings)
- [User photos aren't synced from on-premises to Exchange Online](https://learn.microsoft.com/exchange/troubleshoot/administration/user-photos-not-synced-to-exchange-online)
- [About shared mailboxes – Microsoft 365 admin](https://learn.microsoft.com/microsoft-365/admin/email/about-shared-mailboxes)
- [Graph SDK issue #1974: cannot update the photo of a Bookings mailbox](https://github.com/microsoftgraph/msgraph-sdk-powershell/issues/1974)
- [How to change a photo in a shared mailbox? – Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/4613011/how-to-change-a-photo-in-a-shared-mailbox)
- [Set-MgGroupPhotoContent – Microsoft Graph PowerShell](https://learn.microsoft.com/powershell/module/microsoft.graph.groups/set-mggroupphotocontent)
- [Information about profile picture synchronization in Microsoft 365](https://support.microsoft.com/en-us/office/information-about-profile-picture-synchronization-in-microsoft-365-20594d76-d054-4af4-a660-401133e3d48a)
- [Contact photos don't show in Outlook – troubleshooting](https://learn.microsoft.com/outlook/troubleshoot/user-interface/cannot-see-contact-photos)
- [Microsoft Removes Exchange Online User Photo Cmdlets – Office 365 for IT Pros](https://office365itpros.com/2023/10/09/user-photo-cmdlets/)
- [The photo update settings policy – Office 365 for IT Pros](https://office365itpros.com/2024/09/16/photo-update-settings-policy/)
- [Download users' photos from Exchange Online with PowerShell – Seán McAvinue](https://seanmcavinue.net/2021/10/15/download-users-photos-from-exchange-online-with-powershell/) (pre-Graph approach, historical)
- [CodeTwo Active Directory Photos](https://www.codetwo.com/freeware/active-directory-photos/) (free GUI for `thumbnailPhoto`)
- [How to get user photos by using EWS](https://learn.microsoft.com/exchange/client-developer/exchange-web-services/how-to-get-user-photos-by-using-ews-in-exchange) (on-premises / historical)
