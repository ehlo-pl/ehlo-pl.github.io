+++
title = "Email Header Analysis: What Headers Tell You"
date = 2025-07-07T00:00:00Z
draft = true
tags = ["headers", "authentication", "spf", "dkim", "dmarc", "troubleshooting", "week-23"]
categories = ["Specialized Topics"]
description = "Reading Authentication-Results, tracing the Received chain, and troubleshooting mail flow from the headers alone"
+++

Most of the time nobody looks at an email header. The message arrives, it lands in the
right folder, everyone moves on. The header only becomes interesting the moment something
goes wrong — a message ends up in spam, a customer swears they never got the invoice, or a
phishing report lands in the abuse mailbox and somebody has to decide whether it is real. That is when
the header stops being noise and becomes the single most useful artifact you have.

What I like about headers is that they are an honest log. Every hop that touched the
message wrote a line, and those lines are stacked in order. You do not need access to any
server to read them — the evidence travels with the message. This post is about reading
that evidence: the authentication verdicts, the `Received` trail, and the small
inconsistencies that tell you what actually happened.

This is the *reading* side. The mechanics of how SPF, DKIM, and DMARC actually work — the
DNS records, the signing, the alignment rules — are a separate topic — a DNS-side post on
SPF/DKIM/DMARC is on my list. Here the records are already published and the checks already ran; the
question is how to interpret what the receiving server wrote down.

## Understanding Email Headers

A header is an ordered list of fields, defined by [RFC 5322](https://www.rfc-editor.org/rfc/rfc5322.html).
Each field is a name, a colon, and a value, and the fields you care about mostly fall into
two groups.

The first group is what the author's mail client set: `From`, `To`, `Subject`, `Date`,
`Message-ID`. These are trivial to forge — `From` in particular is just text the sender
typed, which is the whole reason SPF/DKIM/DMARC exist.

The second group is what the mail *infrastructure* added on the way through: `Received`
trace fields, `Authentication-Results`, `Received-SPF`, `DKIM-Signature`, and the ARC
fields. These are the interesting ones, because they were written by servers rather than by
the sender, and — inside an organisation's own systems — the
administrators control them.

The one structural rule that matters for reading: **new fields are prepended to the top.**
Each server that handles the message adds its lines above everything already there. So the
header reads newest-first, top-to-bottom, and the oldest hop — the origin — is at the
bottom. Almost all header analysis comes down to reading from the bottom up.

## Getting the Raw Headers

Before any of the reading, you need the *full* header, not the five lines the mail client
shows by default. Where to find it depends on the client:

- **Outlook (classic):** open the message in its own window, then File → Properties →
  *Internet headers* box.
- **Outlook on the web / new Outlook:** open the message, then More actions → View → *View
  message details*.
- **Gmail:** the three-dot menu on the message → *Show original*. It also prints a small
  SPF/DKIM/DMARC summary at the top, which is convenient but is Gmail's verdict, not the raw
  evidence.
- **Thunderbird:** View → Headers → All, or View Source (`Ctrl+U`) for the whole message.

One trap: **forwarding a message inline destroys the original header.** The forwarder's
client builds a new message. If the header matters, forward as an attachment (`.eml`) or save
the message to a file and work from that.

## Authentication Headers

When a receiving MTA runs authentication checks, it records the outcome in an
`Authentication-Results` header field, standardized in
[RFC 8601](https://www.rfc-editor.org/rfc/rfc8601.html). This is the field that tells you,
in one place, what the receiver decided about SPF, DKIM, and DMARC.

Here is the shape of one (illustrative — generic domains, not a real capture):

```text
Authentication-Results: mx.example.com;
	spf=pass smtp.mailfrom=newsletter.example.net;
	dkim=pass header.d=example.net header.s=selector1;
	dmarc=pass (p=reject sp=reject dis=none) header.from=example.net
```

Read it left to right. The first token — `mx.example.com` — is the **authserv-id**: the
identity of the server that performed the checks and stamped this line. That identity is
not decoration. It is the anchor of the entire trust model.

### The trust boundary (why the authserv-id matters)

RFC 8601 §1.2 is blunt about this: an `Authentication-Results` header is only meaningful if
it was added by a server inside the receiving organisation's trust boundary — its
Administrative Management Domain. Anyone on the internet can put a line reading `dkim=pass` into a message. There is
nothing cryptographic stopping them. The only thing that makes the header trustworthy is
that the organisation's own border MTA added it, after *actually running* the check, and that the border
MTA strips any pre-existing `Authentication-Results` claiming to come from its own
authserv-id (RFC 8601 §5) before adding its own.

So the first question when reading these headers is never "does it say pass?" It is "who
signed this verdict, and is that host inside the boundary?" A pass from the organisation's own inbound gateway means
something. A pass in a header added three hops upstream, by a server you have never heard
of, means nothing — the sender could have written it themselves.

### SPF, DKIM, DMARC Results

Each method reports a result keyword and the identity it checked against. The keywords worth
recognizing:

- **spf** — `pass`, `fail`, `softfail`, `neutral`, `none`, `temperror`, `permerror`. The
  identity is `smtp.mailfrom` (the envelope sender / `MAIL FROM`), *not* the `From:` header.
  This distinction is the source of endless confusion. SPF authenticates the envelope, which
  the recipient never sees.
- **dkim** — `pass`, `fail`, `none`, etc. Reported with `header.d` (the signing domain) and
  `header.s` (the selector). A `dkim=pass` proves the message was signed by whoever controls
  `header.d` and was not altered in the signed portion — it says nothing, on its own, about
  the visible `From`.
- **dmarc** — `pass` or `fail`. DMARC is the field that ties the other two back to the
  domain the human actually sees, `header.from`.

The reason DMARC exists is **alignment**, and alignment is the single most common thing
people misread. SPF checks the envelope `MAIL FROM`; DKIM checks whatever domain chose to
sign. Neither is required to match the `From:` your user reads. DMARC passes only if *at
least one* of them both passes **and** aligns with the `From:` domain. That is why you can
see this and it is completely correct:

```text
spf=pass smtp.mailfrom=bounces.mailer.example
dkim=pass header.d=mailer.example
dmarc=fail header.from=yourbank.example
```

Both underlying checks passed — for `mailer.example`. But the visible `From:` says
`yourbank.example`, nothing aligned to it, so DMARC failed. Two green lights and still a
fail. When someone reports "SPF passed but the mail was rejected," this is almost always
what happened: passing is not the same as aligning.

### Anatomy of a DKIM-Signature

`dkim=pass` in `Authentication-Results` is the receiver's summary. The evidence is the
`DKIM-Signature` field in the message itself, and it is worth being able to read one. An
illustrative example (generic domains, shortened values):

```text
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; d=example.net;
	s=selector1; t=1751876100; h=from:to:subject:date:message-id;
	bh=47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=;
	b=dGVzdHNpZ25hdHVyZQ==
```

[RFC 6376 §3.5](https://www.rfc-editor.org/rfc/rfc6376.html#section-3.5) requires seven tags,
and those are the ones I read first:

- `v` — version, always `1`.
- `a` — signing algorithm, e.g. `rsa-sha256`.
- `d` — the signing domain. This is what DKIM alignment compares with `From:`.
- `s` — the selector. The public key lives in DNS at `<s>._domainkey.<d>`.
- `h` — the list of header fields that were signed. If `From` is missing from it, be
  suspicious.
- `bh` — hash of the body. If the body changed in transit, the receiver's recalculated hash
  no longer matches.
- `b` — the signature itself, over the signed headers and the DKIM-Signature field.

The optional tags that matter for reading: `c` (canonicalization — `relaxed` tolerates
whitespace changes, `simple` almost none), `t` (signing timestamp), `x` (expiry), `i` (the
signing identity) and `q` (key lookup method, `dns/txt`). `l`, a body length limit, is the one
I treat with suspicion: it means only the first *n* bytes of the body are signed, so anything
appended afterwards stays outside the signature.

A message can carry several `DKIM-Signature` fields — the author's domain and the sending
service often both sign. Read the `d=` of each one; a pass for the wrong domain is the
alignment problem from the previous section again.

## Tracing Mail Flow Through Systems

The `Received` fields are the message's itinerary. Each is a trace field added by one hop,
defined in [RFC 5321 §4.4](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.4). Read
bottom to top to follow the message from origin to inbox.

An illustrative pair, oldest at the bottom:

```text
Received: from mx.example.com (mx.example.com [203.0.113.10])
	by mailstore.example.com with LMTP id 9XYZ
	for <alice@example.com>; Mon, 07 Jul 2025 10:15:03 +0200
Received: from mail.example.net (mail.example.net [198.51.100.25])
	by mx.example.com (Postfix) with ESMTPS id 4ABCD1234
	for <alice@example.com>; Mon, 07 Jul 2025 10:15:02 +0200
```

The bottom line is the first hop this infrastructure saw: `mx.example.com` received the
message *from* `mail.example.net` at IP `198.51.100.25`. The `from` clause records what the
connecting host announced in `HELO`/`EHLO` and, in brackets, the reverse-DNS name and the
actual TCP source IP — and that IP in brackets is the one the receiver could not fake,
because it came from the connection itself. The `with ESMTPS` token tells you the hop used
STARTTLS; a bare `with ESMTP` or `SMTP` means it did not.

A few things the `Received` chain reveals quickly:

- **The real origin IP.** The bottom-most external `Received` added by the organisation's own boundary is
  where the message truly entered. Everything below that was written by servers outside
  that boundary and can be fabricated — same trust-boundary logic as the authentication headers.
- **Time spent in transit.** Compare timestamps between hops. A multi-hour gap between two
  lines usually means a queue somewhere retried a deferred message.
- **Loops and unexpected detours.** A message bouncing through a host that should not be in
  the path, or the same server appearing twice, shows up here immediately.

You will also often see `Received-SPF` as its own field, which is the same SPF result as in
`Authentication-Results` but written by the SPF checker in RFC 7208 style — handy because it
spells out the reasoning, e.g. `client-ip=` and the domain it evaluated.

### When intermediaries break authentication

Mailing lists and forwarders are where clean authentication goes to die. A list that appends
a footer changes the body, so the original DKIM signature no longer verifies; forwarding
changes the envelope sender, so SPF now evaluates the forwarder, not the origin. The message
is perfectly legitimate and DMARC fails anyway.

This is exactly the problem the Authenticated Received Chain
([RFC 8617](https://www.rfc-editor.org/rfc/rfc8617.html)) was built for. ARC lets each
intermediary record the authentication results *it* saw, sealed so a later receiver can tell
that authentication passed before the forwarder touched the message and only broke because
of legitimate handling. If you see `ARC-Authentication-Results`, `ARC-Message-Signature`,
and `ARC-Seal` fields, the message passed through something that understood this — and a
`dmarc=fail` on such a message is worth a second look before you treat it as hostile.

## Consistency Checks: Where Forgeries Show

Authentication verdicts can be correct and the message still be wrong. A second pass over the
fields the sender controls often exposes the story. None of these is proof on its own —
legitimate bulk senders trip several of them routinely — but a combination is hard to explain.

- **`Return-Path` vs `From`.** `Return-Path` is the envelope sender written by the final
  receiving server; it is what SPF checked. A different domain is normal for mailing services
  and newsletters, so the question is whether the relationship makes sense.
- **`Reply-To` vs `From`.** A reply address on a different domain than the visible sender is a
  classic business-email-compromise pattern: the message looks internal, the answer goes
  elsewhere.
- **`Message-ID` domain.** Mail clients and servers usually generate it from their own
  hostname. A `Message-ID` ending in an unrelated domain, or in a hostname that has nothing to
  do with the claimed sender, is a hint about what software really produced the message.
- **`HELO` vs reverse DNS in `Received`.** The first part of the `from` clause is what the
  connecting host claimed; the bracketed name and IP come from the connection. A claim of
  `mail.bigcompany.example` from an IP whose PTR is a residential address is worth noting.
- **`Date` and time zones.** Compare the `Date` the client set with the timestamps in the
  `Received` lines. A message claiming to be written at 09:00 in one time zone but entering the
  first server six hours earlier or later deserves a second look.

## Practical Troubleshooting Examples

The patterns above are what you match a real header against. A useful mental checklist when
a message misbehaves:

1. **Find the authserv-id.** Was the `Authentication-Results` line added by a host inside
   the trust boundary? If not, ignore its verdict entirely.
2. **Check alignment, not just the pass/fail keywords.** If SPF and DKIM pass but DMARC
   fails, compare `smtp.mailfrom` / `header.d` against `header.from`. Almost always an
   alignment problem, not a "broken" record.
3. **Read the `Received` chain bottom-up** to find the true origin IP and confirm it matches
   what SPF evaluated.
4. **Look for an ARC set** before condemning a forwarded or list message.

Turning that checklist into concrete, annotated captures is where real examples earn their
keep — a genuine failure reads very differently from a described one.

> **NEEDS YOUR LAB:** annotated real headers from your own captures for 2–3 scenarios:
> (1) a clean `dmarc=pass` message for reference, (2) an alignment failure where SPF/DKIM
> pass but DMARC fails, and (3) a forwarded or mailing-list message showing an ARC set with
> the original DKIM broken. Paste each full header block and highlight the authserv-id,
> the alignment identities, and the origin `Received` line.

> **NEEDS YOUR LAB:** if you have a Mailpit / lab capture of a message before and after a
> list footer is appended, that side-by-side is the clearest possible illustration of why
> DKIM breaks on modification — worth including here.

## Vendor Headers: What the Spam Filter Added

Besides the standard fields, every filtering product writes its own. They are not
standardized, so each needs its own documentation, but the pattern is the same: a verdict, a
score or category, and the reasons.

### Microsoft 365 / Exchange Online

Exchange Online Protection adds `X-Forefront-Antispam-Report` with semicolon-separated
fields. These are the ones I look at first
([Microsoft Learn](https://learn.microsoft.com/en-us/defender-office-365/message-headers-eop-mdo)
has the complete table):

- `CIP` — the connecting IP address, and `PTR` — its reverse DNS name.
- `H` — the `HELO`/`EHLO` string the sender announced.
- `DIR` — direction: `INB` inbound, `OUB` outbound, `INT` internal.
- `SFV` — the spam filtering verdict. `NSPM` means not spam, `SPM` means the spam filter
  flagged it, `SKS` means a mail flow rule marked it as spam before the filter ran, `SKN`
  means a rule marked it as non-spam, and `BULK` means bulk mail.
- `CAT` — the protection category that applied, such as `SPM`, `PHSH`, `MALW`, `SPOOF` or
  `BULK`.
- `SCL` — the spam confidence level. I treat it as a hint and read `SFV` and `CAT` first,
  because those say *why* the message went where it did.

`X-Microsoft-Antispam` carries `BCL`, the bulk complaint level. And `Authentication-Results`
in Microsoft 365 contains an extra method, `compauth` (composite authentication), with a
`reason=` code:

```text
compauth=fail reason=001
```

`compauth` is Microsoft's own decision combining SPF, DKIM, DMARC and sender reputation, and
it is what actually drives spoof handling. The `reason` is a three-digit code (in the Learn
table, `0xx` values are failures and `1xx` values are passes), so look the exact number up
instead of guessing. When a message with `spf=pass` and `dkim=pass` is still treated as spoofed,
`compauth` is usually where the answer is.

### SpamAssassin, Rspamd and Stalwart

Open-source filters write their verdict in plain, readable fields:

- **SpamAssassin** writes `X-Spam-Status: Yes, score=7.2 required=5.0 tests=...` — the list of
  triggered rules is right there.
- **Rspamd** writes `X-Spamd-Result` with the action, the score against the threshold, and
  per-symbol scores, plus a compact `X-Spamd-Bar` made of `+`, `-` or `/` characters.
- **Stalwart** writes its own `X-Spam-Status`, `X-Spam-Result` and `X-Spam-Score` fields.

> **NEEDS YOUR LAB:** a real Microsoft 365 header from your tenant with the
> `X-Forefront-Antispam-Report` and `compauth` lines highlighted (redact tenant names and
> addresses), and one real spam verdict from your Stalwart lab so the field format shown here
> is the one it actually writes. I have not verified Stalwart's exact output format.

## Tools That Do the Reading

Once the structure is familiar, a tool saves time on long headers:

- **Microsoft Message Header Analyzer** — parses a pasted header into a hop-by-hop table with
  delays, and understands the Microsoft anti-spam fields.
- **Google Admin Toolbox Messageheader** — the equivalent from Google, with a clear delay
  breakdown between hops.
- **PowerShell:** for Exchange Online, I covered a module that explains the spam verdict in my
  post on Icewolf.EXO.SpamAnalyze, and CIAOPS publishes an `email-header-report.ps1` script for
  header reports.

Headers contain addresses, internal hostnames and IPs. Redact them before pasting a real
message into any third-party web tool.

> **NEEDS YOUR LAB:** a screenshot of the same lab header run through one of these analyzers,
> next to your manual reading, would show what the tool adds and what it hides.

## Closing Thought

Header analysis is not really a skill about email so much as a skill about not trusting the
sender's word for anything. Once the trust-boundary idea clicks — that only the lines the
receiving infrastructure wrote mean anything, and everything below them is just a claim — the rest
is mechanical. Read bottom-up, check the authserv-id, check alignment, and the header stops
being a wall of text and starts being a fairly honest confession of what the message did on
its way in.

## References

- [RFC 5321 — Simple Mail Transfer Protocol](https://www.rfc-editor.org/rfc/rfc5321.html) (§4.4, the `Received` trace field)
- [RFC 5322 — Internet Message Format](https://www.rfc-editor.org/rfc/rfc5322.html)
- [RFC 8601 — Message Header Field for Indicating Message Authentication Status](https://www.rfc-editor.org/rfc/rfc8601.html) (`Authentication-Results`, trust boundaries in §1.2)
- [RFC 7208 — Sender Policy Framework (SPF)](https://www.rfc-editor.org/rfc/rfc7208.html)
- [RFC 6376 — DomainKeys Identified Mail (DKIM) Signatures](https://www.rfc-editor.org/rfc/rfc6376.html) (§3.5, the `DKIM-Signature` tags)
- [RFC 7489 — Domain-based Message Authentication, Reporting, and Conformance (DMARC)](https://www.rfc-editor.org/rfc/rfc7489.html)
- [RFC 8617 — The Authenticated Received Chain (ARC) Protocol](https://www.rfc-editor.org/rfc/rfc8617.html)
- [Microsoft Learn — Anti-spam message headers in Microsoft 365](https://learn.microsoft.com/en-us/defender-office-365/message-headers-eop-mdo)
- [Gmail Help — Trace an email with its full headers](https://support.google.com/mail/answer/29436)
- [Google Admin Toolbox — Messageheader](https://toolbox.googleapps.com/apps/messageheader/)
