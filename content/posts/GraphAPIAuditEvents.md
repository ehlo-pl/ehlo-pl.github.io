+++
date = '2026-06-27T13:33:31+02:00'
draft = true
title = 'GraphAPIAuditEvents'
+++

# Into

If you agreed any other method to access to mail system then standard access it always happen issues on governance of it. In case of POP3/IMAP/EWS (if you do not care about set-CASMailbox setting properly) it's usually nightmare of debug text connections logs (or worse IIS W3C logs). In case of Exchange Online it's by design impossible.  There are some reports (ironically not on Exchange Online but on admin.cloud.microsoft site, with realistically for Exchange admis available only wit Exchange Administrator (or Report Reader) roles. But it's still not enough. 

In case of Graph API most of members of Service Reader has some access to Defender for office 365 and advanced hunting - so some local Defender buffer of security related events https://security.microsoft.com/v2/advanced-hunting - and ability to ask some KQLs quires. 

First approach (I recommend use it first on one day, not month) is show all application IDs used for Graph API in Exchange context. Something like that: 
```KQL
GraphAPIAuditEvents
| where ResourceDisplayName == "Exchange"
    or RequestUri startswith "/v1.0/users"
    or RequestUri has "mail"
    or RequestUri has "messages"
    or RequestUri has "mailFolders"
| summarize Count = count() by ApplicationId
| sort by Count desc

```

Sometimes it's required to verify permissions:
```KQL
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

and typical issue (as list above will be toooooooooo huge to analyze it) you will need to limit it to some already know applications: 
```KQL
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

There some obstacles in that method of investigation - typical for real life KQL sessions \
- if you will be too aggressive it's possible that you will consume whole short term tenant queires quota. 
- please take care on characters cases in tables - it's case sensitives- I lost few hours because on MS documentation and on some other blog in title (but in other place was OK) `GraphAPIAuditEvents` was written as `GraphApiAuditEvents` (PI in API was in small cases).
-
