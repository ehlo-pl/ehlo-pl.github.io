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
phishing report lands on your desk and you have to decide whether it is real. That is when
the header stops being noise and becomes the single most useful artifact you have.

What I like about headers is that they are an honest log. Every hop that touched the
message wrote a line, and those lines are stacked in order. You do not need access to any
server to read them — the evidence travels with the message. This post is about reading
that evidence: the authentication verdicts, the `Received` trail, and the small
inconsistencies that tell you what actually happened.

This is the *reading* side. The mechanics of how SPF, DKIM, and DMARC actually work — the
DNS records, the signing, the alignment rules — are covered in the earlier DNS post on
SPF/DKIM/DMARC. Here the records are already published and the checks already ran; the
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
the sender, and — inside your own systems — you control them.

The one structural rule that matters for reading: **new fields are prepended to the top.**
Each server that handles the message adds its lines above everything already there. So the
header reads newest-first, top-to-bottom, and the oldest hop — the origin — is at the
bottom. Almost all header analysis comes down to reading from the bottom up.

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
it was added by a server inside your own trust boundary — your Administrative Management
Domain. Anyone on the internet can put a line reading `dkim=pass` into a message. There is
nothing cryptographic stopping them. The only thing that makes the header trustworthy is
that *your* border MTA added it, after *actually running* the check, and that your border
MTA strips any pre-existing `Authentication-Results` claiming to come from your own
authserv-id (RFC 8601 §5) before adding its own.

So the first question when reading these headers is never "does it say pass?" It is "who
signed this verdict, and do I trust that host?" A pass from your own inbound gateway means
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

## Tracing Mail Flow Through Systems

The `Received` fields are the message's itinerary. Each is a trace field added by one hop,
defined in [RFC 5321 §4.4](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.4). Read
bottom to top to follow the message from origin to inbox.

An illustrative pair, oldest at the bottom:

```text
Received: from mx.example.com (mx.example.com [203.0.113.10])
	by mailstore.example.com with LMTP id 9XYZ
	for <alice@example.com>; Tue, 07 Jul 2025 10:15:03 +0200
Received: from mail.example.net (mail.example.net [198.51.100.25])
	by mx.example.com (Postfix) with ESMTPS id 4ABCD1234
	for <alice@example.com>; Tue, 07 Jul 2025 10:15:02 +0200
```

The bottom line is the first hop your infrastructure saw: `mx.example.com` received the
message *from* `mail.example.net` at IP `198.51.100.25`. The `from` clause records what the
connecting host announced in `HELO`/`EHLO` and, in brackets, the reverse-DNS name and the
actual TCP source IP — and that IP in brackets is the one the receiver could not fake,
because it came from the connection itself. The `with ESMTPS` token tells you the hop used
STARTTLS; a bare `with ESMTP` or `SMTP` means it did not.

A few things the `Received` chain reveals quickly:

- **The real origin IP.** The bottom-most external `Received` added by your own boundary is
  where the message truly entered. Everything below that was written by servers you do not
  control and can be fabricated — same trust-boundary logic as the authentication headers.
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

## Practical Troubleshooting Examples

The patterns above are what you match a real header against. A useful mental checklist when
a message misbehaves:

1. **Find the authserv-id.** Was the `Authentication-Results` line added by a host you
   trust? If not, ignore its verdict entirely.
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

## Closing Thought

Header analysis is not really a skill about email so much as a skill about not trusting the
sender's word for anything. Once the trust-boundary idea clicks — that only the lines your
own infrastructure wrote mean anything, and everything below them is just a claim — the rest
is mechanical. Read bottom-up, check the authserv-id, check alignment, and the header stops
being a wall of text and starts being a fairly honest confession of what the message did on
its way to you.

## References

- [RFC 5321 — Simple Mail Transfer Protocol](https://www.rfc-editor.org/rfc/rfc5321.html) (§4.4, the `Received` trace field)
- [RFC 5322 — Internet Message Format](https://www.rfc-editor.org/rfc/rfc5322.html)
- [RFC 8601 — Message Header Field for Indicating Message Authentication Status](https://www.rfc-editor.org/rfc/rfc8601.html) (`Authentication-Results`, trust boundaries in §1.2)
- [RFC 7208 — Sender Policy Framework (SPF)](https://www.rfc-editor.org/rfc/rfc7208.html)
- [RFC 6376 — DomainKeys Identified Mail (DKIM) Signatures](https://www.rfc-editor.org/rfc/rfc6376.html)
- [RFC 7489 — Domain-based Message Authentication, Reporting, and Conformance (DMARC)](https://www.rfc-editor.org/rfc/rfc7489.html)
- [RFC 8617 — The Authenticated Received Chain (ARC) Protocol](https://www.rfc-editor.org/rfc/rfc8617.html)
