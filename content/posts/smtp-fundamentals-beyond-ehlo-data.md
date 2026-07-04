+++
title = "SMTP Fundamentals: Beyond EHLO and DATA"
date = 2025-02-24T00:00:00Z
draft = true
tags = ["smtp", "protocols", "relay", "authentication", "week-04"]
categories = ["Classical Protocols"]
description = "Protocol flow with real examples, relay concepts, and common implementation gotchas"
+++

Everybody who has ever poked at a mail server by hand knows the four verbs: `EHLO`,
`MAIL FROM`, `RCPT TO`, `DATA`. You type them, the server answers with three-digit codes,
a message gets queued. That part is easy — it fits on a napkin.

What I keep coming back to is everything *around* those four verbs: the split between the
envelope and the message, the capability negotiation that happens right after `EHLO`, and
the difference between a server that relays mail and one that merely accepts your
submission. That is where the actual behaviour of an email system lives, and it is also
where most of the surprises hide. So this is SMTP beyond the napkin.

The base protocol is [RFC 5321](https://www.rfc-editor.org/rfc/rfc5321.html); the message
format that travels inside `DATA` is [RFC 5322](https://www.rfc-editor.org/rfc/rfc5322.html).
Keep those two apart in your head and half of SMTP stops being confusing.

## SMTP Protocol Flow

A session is a short, strict conversation. The client speaks a command, the server
answers with a reply code, and neither side moves on until that exchange is done. Here is
a full plaintext session against a lab server on port 25, typed by hand:

```text
$ telnet mail.example.com 25
Trying 203.0.113.10...
Connected to mail.example.com.
220 mail.example.com ESMTP Postfix
EHLO client.example.net
250-mail.example.com
250-PIPELINING
250-SIZE 10240000
250-STARTTLS
250-AUTH PLAIN LOGIN
250-8BITMIME
250 CHUNKING
MAIL FROM:<alice@example.net>
250 2.1.0 Ok
RCPT TO:<bob@example.com>
250 2.1.5 Ok
DATA
354 End data with <CR><LF>.<CR><LF>
From: Alice <alice@example.net>
To: Bob <bob@example.com>
Subject: Testing SMTP by hand

Hello Bob, this is the message body.
.
250 2.0.0 Ok: queued as 4F1B2C3D
QUIT
221 2.0.0 Bye
```

Two things in there matter more than they look:

**`EHLO` is a negotiation, not a greeting.** The multi-line `250-` reply is the server
announcing its ESMTP extensions ([RFC 1869](https://www.rfc-editor.org/rfc/rfc1869.html)).
Everything the client is allowed to do next — authenticate, start TLS, send 8-bit
content, respect a size limit — is decided by that list. `SIZE`
([RFC 1870](https://www.rfc-editor.org/rfc/rfc1870.html)), `8BITMIME`
([RFC 6152](https://www.rfc-editor.org/rfc/rfc6152.html)) and `STARTTLS` are not
decorations; they change what a correct client does. The last line uses `250 ` (space)
instead of `250-` (dash) — that is how the client knows the capability list is finished.

**The envelope is not the message.** `MAIL FROM` and `RCPT TO` are the *envelope* — that
is what the server actually routes on. The `From:` and `To:` lines inside `DATA` are just
text in the message; the server does not deliver by them. This is why a message can arrive
addressed "To: everyone" while the envelope quietly named only you, and it is the seam
that SPF and DMARC later pull on. Worth internalising early.

> **NEEDS YOUR LAB:** replace the transcript above (or add alongside it) with a real
> capture from your mailpit setup — including mailpit's web UI showing the received
> message and how it presents the envelope vs. header sender.

## Relay Concepts

### Open Relay vs Authenticated Submission

The single most useful distinction in running SMTP is *relay* versus *submission*, and it
maps almost cleanly onto ports.

- **Port 25 — relay (MTA to MTA).** This is how one mail server hands mail to another
  across the internet. It is unauthenticated by design: the sending server is a stranger.
  A port-25 server should therefore accept mail only for domains it is responsible for.
- **Port 587 — submission (MUA to MTA).** This is where *your* mail client hands a message
  to *your* server to send onward. It is defined separately in
  [RFC 6409](https://www.rfc-editor.org/rfc/rfc6409.html) precisely so it can play by
  stricter rules — authentication is required
  ([RFC 4954](https://www.rfc-editor.org/rfc/rfc4954.html), the `AUTH` extension), and the
  connection should be encrypted with `STARTTLS`
  ([RFC 3207](https://www.rfc-editor.org/rfc/rfc3207.html)).

The failure everyone fears is the **open relay**: a server that accepts mail from anyone,
for any destination, and forwards it. That is a spammer's dream and it will get your IP
onto blocklists within hours. The fix is the rule above — port 25 relays only for your own
domains; anything going to the outside world must come in authenticated on 587.

There is also **port 465**, implicit TLS submission. It was deprecated years ago, then
reinstated by [RFC 8314](https://www.rfc-editor.org/rfc/rfc8314.html), which declares
cleartext mail obsolete and pushes all submission onto TLS (465 or 587). So the modern
picture is: 25 for server-to-server relay, 587 (STARTTLS) or 465 (implicit TLS) for
authenticated submission.

> **NEEDS YOUR LAB:** the corresponding relay/submission restriction config from your lab
> server (for Postfix, the `smtpd_relay_restrictions` and submission-service block in
> `master.cf`) belongs here, with a note on what each line does. Detailed hardening gets
> its own post — link it once written.

## Common Implementation Gotchas

These are the ones that cost real time, roughly in the order I have hit them:

- **CRLF line endings.** SMTP lines end with `\r\n`, not a bare `\n`. Hand-rolled clients
  that send Unix line endings produce messages that some servers reject and others accept
  and mangle. If a message "looks fine but breaks", check the line endings first.
- **Dot-stuffing.** A single `.` on its own line ends `DATA`. So any body line that starts
  with a dot must be sent doubled (`..`), and the receiver strips one back off. Forget this
  and a message body containing a leading dot will be silently truncated.
- **Envelope vs. header mismatch.** As above — debugging a "wrong sender" problem by
  staring at the `From:` header while the envelope `MAIL FROM` says something else is a
  classic dead end.
- **`SIZE` limits.** The server advertises `SIZE` in its `EHLO` reply for a reason. Push a
  message past it and you get a `552` rejection, sometimes only *after* the whole `DATA`
  transfer — annoying to diagnose if you did not read the capability line.
- **HELO/EHLO name and reverse DNS.** Many receivers check that your announced hostname
  and your IP's PTR record line up. A lab box with no PTR, or one announcing
  `localhost.localdomain`, will get greylisted or refused by strict peers.
- **Implicit vs. explicit TLS confusion.** Pointing a client at port 465 while expecting
  `STARTTLS`, or at 587 while expecting implicit TLS, produces a hang or a handshake error
  that looks like a firewall problem but is not.

> **NEEDS YOUR LAB:** for each gotcha you have actually reproduced in the lab, drop in the
> log line or error response you saw (mailpit / Postfix logs). Real failure output is far
> more convincing than my description of it.

## Practical Examples

The fastest way to *feel* the protocol is still to speak it yourself. On a box with
`telnet` (or `nc`), the plaintext walkthrough is the session shown at the top of this
post — connect to port 25, `EHLO`, `MAIL FROM`, `RCPT TO`, `DATA`, end with a lone dot.
Reading the server's reply codes as you go teaches more than any diagram.

For anything with `STARTTLS` or `AUTH`, plain `telnet` stops being enough — you need a TLS
client. `openssl s_client -starttls smtp -connect mail.example.com:587` gets you an
encrypted session you can then type into, and it is the tool I reach for when a submission
port "should work but doesn't".

> **NEEDS YOUR LAB:** this section is where your own screenshots carry the weight —
> the telnet exchange against your lab server, the mailpit UI catching the message, and an
> `openssl s_client` STARTTLS handshake on 587. Capture those from the running lab and
> drop them in; the protocol notes above are the frame, your captures are the picture.

## References

- [RFC 5321 — Simple Mail Transfer Protocol](https://www.rfc-editor.org/rfc/rfc5321.html)
- [RFC 5322 — Internet Message Format](https://www.rfc-editor.org/rfc/rfc5322.html)
- [RFC 1869 — SMTP Service Extensions (ESMTP)](https://www.rfc-editor.org/rfc/rfc1869.html)
- [RFC 6409 — Message Submission for Mail](https://www.rfc-editor.org/rfc/rfc6409.html)
- [RFC 4954 — SMTP Service Extension for Authentication](https://www.rfc-editor.org/rfc/rfc4954.html)
- [RFC 3207 — SMTP Extension for Secure SMTP over TLS (STARTTLS)](https://www.rfc-editor.org/rfc/rfc3207.html)
- [RFC 8314 — Cleartext Considered Obsolete: Use of TLS for Email](https://www.rfc-editor.org/rfc/rfc8314.html)
- [mailpit — a mail testing tool for developers](https://mailpit.axllent.org/)
