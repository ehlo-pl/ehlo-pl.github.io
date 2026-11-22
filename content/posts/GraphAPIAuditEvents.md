+++
date = '2026-06-27T13:33:31+02:00'
draft = false
title = 'Hunting Graph API access to Exchange with GraphAPIAuditEvents'
description = "Hunting which apps access Exchange mailboxes over Graph API using the GraphAPIAuditEvents advanced-hunting table in Microsoft Defender."
tags = ["graph-api", "exchange-online", "microsoft-365", "defender-xdr", "advanced-hunting", "kql"]
categories = ["Microsoft 365"]
+++

## Intro

Any time you agree to a way of reaching the mail system other than the standard one, you
end up with a governance problem. With POP3/IMAP/EWS (assuming you did not bother to set
`Set-CASMailbox` properly) it's usually the nightmare of debugging text connection logs -
or, even worse, IIS W3C logs. With Graph API it is by design almost impossible: there is
no per-message protocol log you can just `Get-` from Exchange Online. There are some
reports, but - ironically - not in Exchange itself; they live on the `admin.cloud.microsoft`
site, and realistically an Exchange admin only sees them with the Exchange Administrator
(or Report Reader) role. And even that is not enough.

For Graph API most members holding the Security Reader role already have some access to
Microsoft Defender for Office 365 and to advanced hunting - a local, security-focused
buffer of events at <https://security.microsoft.com/v2/advanced-hunting> - and the ability
to run KQL queries against it. The table that finally fills the gap for Graph read
operations is `GraphAPIAuditEvents`.

## Some queries examples

The first approach (and I recommend running it first for a single day, not a whole month)
is to list every application ID that used Graph API in an Exchange context. Something like
this:

```kql
GraphAPIAuditEvents
| where TargetWorkload == "Microsoft.Exchange"
    or RequestUri startswith "/v1.0/users"
    or RequestUri has "mail"
    or RequestUri has "messages"
    or RequestUri has "mailFolders"
| summarize Count = count() by ApplicationId
| sort by Count desc
```

Sometimes it's necessary to verify permissions instead:

```kql
let exchangePerms = dynamic([
    "Mail.Read",
    "Mail.ReadBasic",
    "Mail.ReadWrite",
    "Mail.Send",
    "MailboxSettings.Read",
    "MailboxSettings.ReadWrite",
    "MailFolders.Read",
    "MailFolders.ReadWrite"
]);

GraphAPIAuditEvents
| where Scopes has_any (exchangePerms)
| summarize Count = count() by ApplicationId
| sort by Count desc
```

> **Note:** double-check the scope names against the app's actual API permissions.
> `MailFolders.Read` / `MailFolders.ReadWrite` are not standard Graph scopes (mail folders
> are reached through `Mail.Read*`), so keep the list honest for your tenant.

And the typical problem - the list above is usually **way** too huge to analyze - means you
will need to limit it to a few already known applications:

```kql
let appIds = dynamic([
    "12345678-285b-4a8c-89dc-987654321012",
    "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "11111111-2222-3333-4444-555555555555"
]);

GraphAPIAuditEvents
| where ApplicationId in (appIds)
| project Timestamp, AccountObjectId, ServicePrincipalId, RequestMethod, RequestUri, ResponseStatusCode, Scopes
| sort by Timestamp desc
```

## Obstacles

There are a few obstacles in this method of investigation - the ones typical for real-life
KQL sessions:

- If you are too aggressive you can burn the whole short-term tenant query quota in one
  session.
- Mind the character case in table and column names - KQL is case-sensitive. I lost a few
  hours because Microsoft documentation and some blog wrote the table as
  `GraphApiAuditEvents` (with a lowercase "pi" in API), while in another place it was
  spelled `GraphAPIAuditEvents`. Use the casing that your Advanced Hunting actually
  resolves and stick to it.
- The good news: `GraphAPIAuditEvents` is part of the Defender XDR / advanced hunting
  tables, so there is no extra ingestion or storage cost - you only need the relevant
  portal access to query it.

## References

- [GraphApiAuditEvents table in the advanced hunting schema](https://learn.microsoft.com/en-us/defender-xdr/advanced-hunting-graphapiauditevents-table)
- [GraphApiAuditEvents: The new Graph API Logs](https://kqlquery.com/posts/graphapiauditevents/) by [Bert-Jan Pals](https://www.linkedin.com/in/bert-janpals/)
 2025-08-19
- [Advanced hunting query best practices](https://learn.microsoft.com/en-us/defender-xdr/advanced-hunting-best-practices)
- [Advanced hunting portal](https://security.microsoft.com/v2/advanced-hunting)
