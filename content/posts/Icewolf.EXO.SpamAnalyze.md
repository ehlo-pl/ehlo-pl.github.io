+++
title = 'Icewolf.EXO.SpamAnalyze: Why Did Exchange Online Treat This Mail as Spam?'
date = '2026-07-04T13:36:46+02:00'
draft = true
description = "A PowerShell module that walks through the usual message trace investigation for one sender and one recipient - what it checks, what it misses, and what to verify before trusting it"
tags = ["powershell", "exchange-online", "message-trace", "spam", "eop", "troubleshooting"]
categories = ["PowerShell"]
+++

## The Discovery

"Why did this mail land in Junk?" is a ticket every Exchange Online admin knows. The answer is rarely in one place: a message trace, the spam verdict hidden in the trace details, the user's own Safe and Blocked Senders, the anti-spam policy, the Tenant Allow/Block List, a transport rule somebody wrote years ago with SCL -1, and then DNS records of the sender. Doing it by hand takes a dozen cmdlets and a lot of copy and paste.

**Icewolf.EXO.SpamAnalyze** by Andres Bohren puts that checklist into one command. The author describes it as a module that simplifies the message trace in Exchange Online, and as a helper for finding out why a mail was identified as spam or phish. It is also on the standard module list of M365PSProfile, which I wrote about separately.

> **NEEDS YOUR LAB:** the personal part - which real case made you try it (a user complaining about a missing mail? a false positive?), and what you did before.

## What Is It?

A small module by a single author (Andres Bohren, icewolf.ch). It exports exactly one function, `Invoke-SpamAnalyze`. The latest version I found in the PowerShell Gallery is **2.0.15, published on 8 November 2025**. It needs PowerShell 5.1 or later, and works in Windows PowerShell and PowerShell 7.

Two things worth knowing before installing:

- **No license is declared.** The Gallery page shows none, the manifest has the license line commented out, and I did not find a LICENSE file in the repository folder. So "free to download" is not the same as "free to reuse or redistribute"; I would ask the author before bundling it into anything.
- **ExchangeOnlineManagement is still needed.** Version 2.0.15 removed it from the manifest dependencies, but the module file still requires it and calls `Connect-ExchangeOnline`. The module does not use Microsoft Graph.

```powershell
Install-Module -Name Icewolf.EXO.SpamAnalyze -Scope CurrentUser
# or
Install-PSResource -Name Icewolf.EXO.SpamAnalyze

Get-Help Invoke-SpamAnalyze -Full
```

## How to Use It

The command takes the sender and the recipient, and optionally a date range:

```powershell
Invoke-SpamAnalyze -SenderAddress sender@example.com -RecipientAddress user@contoso.com

Invoke-SpamAnalyze -SenderAddress sender@example.com -RecipientAddress user@contoso.com `
  -StartDate (Get-Date).AddDays(-5) -EndDate (Get-Date)
```

Without dates it looks at the last 10 days. Message trace in Exchange Online reaches back 90 days, but a single query can cover only 10 days, so for an older message the start and end date must be set to a window of at most 10 days.

The module is **interactive**. It reuses an existing Exchange Online session or starts a normal interactive sign-in, prints a table of the messages found, and asks for the `MessageTraceId` of the one to analyze (`Read-Host`). Everything it does is read-only - only `Get-*` cmdlets.

> **NEEDS YOUR LAB:** a real run - the message table, the prompt, and the full output for one message (screenshot or pasted text, with names and addresses anonymized). The author's own posts show output only as screenshots, so I found no text sample to base this on.

## What It Checks

I read the module source (768 lines, from the author's GitHub repository) to see what happens after the `MessageTraceId` is chosen. In order:

| Section | Source in Exchange Online |
|---|---|
| Message details and events | `Get-MessageTraceV2` / `Get-MessageTraceDetailV2` (the legacy cmdlets as fallback) |
| Recipient details | `Get-Recipient` |
| Transport rules that set SCL to -1 | `Get-TransportRule` |
| User's junk configuration (trusted lists, blocked senders) | `Get-MailboxJunkEmailConfiguration` |
| Anti-spam policy allowed/blocked senders and domains | `Get-HostedContentFilterPolicy` |
| Tenant Allow/Block List (sender, domain, spoofed senders) | `Get-TenantAllowBlockListItems`, `Get-TenantAllowBlockListSpoofItems` |

From the trace details it picks the *Spam* event and decodes the XML in it: SCL, SFV, DI, the connecting IP (CIP), country, score and a few more fields. The connecting IP is compared with the published Exchange Online Protection IP ranges, and the module marks it as an EOP address or as the EOP relay pool. Finally it asks Google DNS-over-HTTPS for the sender domain's NS, MX, SPF, DKIM (selector1 and selector2) and DMARC records, and prints them.

That DNS part is easy to misread: the module prints the records **as they are today** and does not judge pass or fail. It does not show what Exchange Online evaluated when the message arrived.

## What It Does Not Check

Just as important, from the same source:

- It does **not read raw message headers**. There is no `X-Forefront-Antispam-Report`, no CAT (threat category), no DIR (direction), no `Authentication-Results`.
- It does **not look at quarantine** (`Get-QuarantineMessage`) or at Defender for Office 365 reports and policies.
- It returns **no objects**. Everything is `Write-Host` text, so it is a helpdesk tool, not a building block for a script.

## Where I Would Not Trust It Blindly

This is from reading the code and comparing it with Microsoft Learn; I have not run any of it, so treat it as a list of things to test.

**The legacy cmdlet check.** Since version 2.0.14 (January 2025) the module prefers `Get-MessageTraceV2` and falls back to `Get-MessageTrace`. But the startup check requires **both** cmdlets to exist, and otherwise stops with a "No Permission" message. Microsoft announced that retirement of the legacy message trace cmdlets begins on 1 September 2025. I found no date when the cmdlets are really removed, so I do not know whether a current tenant still has them. If it does not, the module would stop with a message about permissions although V2 works fine.

> **NEEDS YOUR LAB:** does the module start in your tenant today? Check `Get-Command Get-MessageTrace, Get-MessageTraceV2` and then run it.

**Explanations which differ from the documentation.** The module translates some values into plain text, and a few translations disagree with the current Microsoft article about anti-spam message headers:

- **SFV:SKB.** The module explains it like SKA: the sender is on an allow list and the mail goes to the Inbox. Microsoft documents SKB as the message being marked as spam because the sender matched the blocked senders or domains in an anti-spam policy. That is the opposite meaning.
- **SFV:SKI.** The module says intra-organization mail. Microsoft says the source IP was on the connection filter IP Allow List.
- **SCL to folder.** The module maps SCL -1 to 4 to Inbox, 5-6 to Junk and 7-9 to quarantine. Microsoft says that in cloud organizations the SCL does not decide the action, and points to CAT and DIR instead.
- **DI values** (SB, SQ, SD and others) I could not find explained on the Microsoft pages I searched. The meanings rest on the module alone.

**Small code issues**, which I only noticed by reading and which need a test: the subject is cut with `Substring(0,20)`, which should fail on a subject shorter than 20 characters; the selector2 DKIM lookup runs only when selector1 exists; and the allowed/blocked sender comparison uses `-match`, so a dot or a plus sign in an address is treated as a regular expression. There is also no paging and no handling of ranges longer than 10 days, so a busy sender and recipient pair may be cut off at the cmdlet's result limit.

> **NEEDS YOUR LAB:** test the three easy ones: a message with a short subject, a sender domain with only selector2, and a date range wider than 10 days. Note what happens.

**Permissions.** The author documents no roles. Microsoft ties message trace to the Organization Management role group or to the Entra Global Administrator or Exchange Administrator roles, and Tenant Allow/Block List read access to roles like Global Reader and Security Reader. The role needed for each cmdlet the module calls was not verified, so an account with a narrow role may fail halfway through the report.

## Message Trace Changes Around It

The module sits on top of message trace, so it inherits the changes there. The V2 cmdlets keep the 90-day history but limit one query to 10 days, have no paging (the next page is requested with `-EndDate` and `-StartingRecipientAddress`), accept `-ResultSize` up to 5000, and allow 100 requests in 5 minutes. V2 needs ExchangeOnlineManagement 3.7.0 or later. For scripts and automation Microsoft also has a message trace API in Microsoft Graph, which uses application permissions, and which the module does not use. One date I found in two versions: the retirement of the older REST reporting service is given as 18 March 2026 in one Message Center post, and as 8 April 2026 in a later one. It does not touch this module, but it shows how often these dates move.

## Other Tools for the Same Question

Message trace says what happened to the message. The Defender tools say why it was detected:

- **Threat Explorer and Real-time detections** (Defender for Office 365 Plan 2 and Plan 1) show detection technology, threat classification and authentication results, with about 30 days of history.
- **Advanced hunting** (`EmailEvents` table) is filled only when Defender for Office 365 is in use, and keeps 30 days of data by default.
- **Admin submissions** analyze a message again and show which policy or entry affected the result.
- **Header analyzers.** MailHeaderAnalyzer (Rafael Pfister, version 0.2.0 in the Gallery) and the CIAOPS script `email-header-report.ps1` both start from header text, not from a trace, so they complement SpamAnalyze.

Message trace goes back furthest (90 days) and needs no Defender licence, so a trace-based module still makes the most sense in tenants with only the basic Exchange Online Protection.

## Why This Matters

For one sender, one recipient and one complaint, the module gets to the interesting places in a minute: a transport rule with SCL -1, a forgotten entry in the Tenant Allow/Block List, a user's own blocked sender, a connecting IP that is only the EOP relay pool. That is the part I like. The part to be careful with is the text it prints: the colours and sentences read like a verdict, but some of them are simplified or wrong, so the numbers (SCL, SFV, CIP) are worth more than the interpretation. For the interpretation I would go to the current Microsoft article about anti-spam message headers.

## Closing Thought

> **NEEDS YOUR LAB:** your own verdict - did it find the cause in the case you tried, would you give it to the helpdesk, would you fix the SKB text and send the author a pull request, and what to try next.

## References

- [Icewolf.EXO.SpamAnalyze - PowerShell Gallery](https://www.powershellgallery.com/packages/Icewolf.EXO.SpamAnalyze) (version history, requirements)
- [Icewolf.EXO.SpamAnalyze - source and readme (GitHub)](https://github.com/BohrenAn/GitHub_PowerShellScripts/tree/main/Icewolf.EXO.SpamAnalyze)
- [My first PowerShell module: Icewolf.EXO.SpamAnalyze - Andres Bohren, icewolf.ch (2021-05-10)](https://blog.icewolf.ch/archive/2021/05/10/my-first-powershell-module-icewolf-exo-spamanalyze/)
- [Anti-spam message headers - Microsoft Learn](https://learn.microsoft.com/en-us/defender-office-365/message-headers-eop-mdo)
- [Get-MessageTraceV2 - Microsoft Learn](https://learn.microsoft.com/en-us/powershell/module/exchangepowershell/get-messagetracev2)
- [Get-MessageTraceDetailV2 - Microsoft Learn](https://learn.microsoft.com/en-us/powershell/module/exchangepowershell/get-messagetracedetailv2)
- [Message trace in the Exchange admin center - Microsoft Learn](https://learn.microsoft.com/en-us/exchange/monitoring/trace-an-email-message/message-trace-modern-eac)
- [Message trace API in Microsoft Graph - Microsoft Learn](https://learn.microsoft.com/exchange/monitoring/trace-an-email-message/graph-api-message-trace)
- [MC1092458 - retirement of legacy message trace](https://mc.merill.net/message/MC1092458)
- [MC1221939](https://mc.merill.net/message/MC1221939)
- [Threat Explorer and real-time detections - Microsoft Learn](https://learn.microsoft.com/en-us/defender-office-365/threat-explorer-real-time-detections-about)
- [EmailEvents table - Microsoft Learn](https://learn.microsoft.com/en-us/defender-xdr/advanced-hunting-emailevents-table)
- [Admin submissions - Microsoft Learn](https://learn.microsoft.com/en-us/defender-office-365/submissions-admin)
- [MailHeaderAnalyzer - PowerShell Gallery](https://www.powershellgallery.com/packages/MailHeaderAnalyzer)
- [CIAOPS: PowerShell script for analyzing Exchange Online email headers](https://blog.ciaops.com/2025/05/27/powershell-script-for-analyzing-exchange-online-email-headers/)
