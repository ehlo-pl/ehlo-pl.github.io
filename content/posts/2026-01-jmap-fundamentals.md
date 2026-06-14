+++
date = '2026-01-25T12:58:46+01:00'
draft = true
title = 'JMAP Fundamentals'
+++


Got it — you want to interact with an email server using JMAP (JSON Meta Application Protocol) via cURL.
JMAP is a modern, JSON-over-HTTP alternative to IMAP/SMTP for email, contacts, and calendars.
Below is a complete runnable example showing how to authenticate and fetch email data using cURL.

## Prerequisites

A JMAP-enabled email provider (e.g., Fastmail, Cyrus IMAP with JMAP, or another server that supports RFC 8620).
Your username, password (or API token), and the JMAP session endpoint (usually https://mail.example.com/.well-known/jmap).


## Step 1 — Discover the JMAP Session Resource

The session resource tells you available accounts, capabilities, and API endpoints.
```bash
curl -u "USERNAME:PASSWORD" \
     -H "Accept: application/json" \
     https://mail.example.com/.well-known/jmap

Response example (truncated):
Json{
  "username": "user@example.com",
  "apiUrl": "https://mail.example.com/jmap/",
  "downloadUrl": "https://mail.example.com/jmap/download/{accountId}/{blobId}/{name}?type={type}",
  "uploadUrl": "https://mail.example.com/jmap/upload/{accountId}/",
  "primaryAccounts": {
    "urn:ietf:params:jmap:mail": "abc123"
  }
}
```

apiUrl → where you send JMAP method calls.
primaryAccounts → your account ID for email.


## Step 2 — Fetch Email Messages

Once you have apiUrl and accountId, you can request messages.
```Bash
curl -u "USERNAME:PASSWORD" \
     -H "Content-Type: application/json" \
     -X POST https://mail.example.com/jmap/ \
     -d '{
           "using": ["urn:ietf:params:jmap:core", "urn:ietf:params:jmap:mail"],
           "methodCalls": [
             ["Email/query", {
               "accountId": "abc123",
               "filter": { "inMailbox": "INBOX" },
               "limit": 5,
               "sort": [{ "property": "receivedAt", "isAscending": false }]
             }, "a"]
           ]
         }'
```
What this does:

Uses Email/query to get the latest 5 messages in the INBOX.
You can then use Email/get to fetch full message details.


## Step 3 — Fetch Full Email Data

After getting message IDs from Email/query, request details:

```bash
curl -u "USERNAME:PASSWORD" \
     -H "Content-Type: application/json" \
     -X POST https://mail.example.com/jmap/ \
     -d '{
           "using": ["urn:ietf:params:jmap:core", "urn:ietf:params:jmap:mail"],
           "methodCalls": [
             ["Email/get", {
               "accountId": "abc123",
               "ids": ["M123", "M124"],
               "properties": ["id", "subject", "from", "receivedAt", "preview"]
             }, "b"]
           ]
         }'
```


## Notes & Best Practices

Authentication: Many servers require OAuth2 or API tokens instead of plain passwords.
Security: Always use HTTPS and avoid storing credentials in plain text.
Batching: JMAP allows multiple method calls in one request for efficiency.

# References
### RFC and Specs references

[jmapio/jmap: JSON Meta Application Protocol Specification (JMAP)](https://github.com/jmapio/jmap)


RFC 8620 — JMAP Core
RFC 8621 — JMAP Mail

## Other sources
[jmap · GitHub Topics](https://github.com/topics/jmap)
[JSON Meta Application Protocol - Wikipedia](https://en.wikipedia.org/wiki/JSON_Meta_Application_Protocol)
 [JMAP Software Implementations](https://jmap.io/software.html)



### Clients
* [Cypht: Lightweight Open Source webmail aggregator](https://www.cypht.org/) \[PHP, JS]. Supports IMAP/SMTP, JMAP and EWS (Exchange Web Services)
* [CLI to synchronize, backup and restore emails](https://github.com/pimalaya/neverest)  [pimalaya.org](https://pimalaya.org/ "https://pimalaya.org") -
* [tmail-flutter](https://github.com/linagora/tmail-flutter)  A multi-platform (Flutter) application for reading your emails, with your favorite devices, using the JMAP protocol!


* Mailtemi is a JMAP/MS Graph/IMAP email app for iOS and Android. It supports multiple email accounts, contacts, and calendars.[\[17\]](https://en.wikipedia.org/wiki/JSON_Meta_Application_Protocol#cite_note-17)
* Ltt.rs is a proof of concept email client for Android that supports only JMAP.[\[18\]](https://en.wikipedia.org/wiki/JSON_Meta_Application_Protocol#cite_note-18)
* Twake Mail is an open source app client for iOS and Android developed by Linagora.[\[19\]](https://en.wikipedia.org/wiki/JSON_Meta_Application_Protocol#cite_note-19)
* aerc is a terminal-based email client, which added support for JMAP in version 0.16[\[20\]](https://en.wikipedia.org/wiki/JSON_Meta_Application_Protocol#cite_note-20)

### Servers

* Since its release of version 3.6.0 in 2021, [Apache Software Foundation](https://en.wikipedia.org/wiki/The_Apache_Software_Foundation "The Apache Software Foundation")’s free mail-server [Apache James](https://en.wikipedia.org/wiki/Apache_James "Apache James") has included support for the JMAP RFCs.[\[12\]](https://en.wikipedia.org/wiki/JSON_Meta_Application_Protocol#cite_note-james-3.6.0-12)[\[13\]](https://en.wikipedia.org/wiki/JSON_Meta_Application_Protocol#cite_note-13) The OpenPaas collaboration platform implements its email and webmail UI using James and JMAP.[\[14\]](https://en.wikipedia.org/wiki/JSON_Meta_Application_Protocol#cite_note-14)
* [Cyrus IMAP](https://en.wikipedia.org/wiki/Cyrus_IMAP_server "Cyrus IMAP server") provisionally supports the JMAP protocol standards as of version 3.8.3, released in May 2024, when built with this functionality.[\[15\]](https://en.wikipedia.org/wiki/JSON_Meta_Application_Protocol#cite_note-15)
* Stalwart Mail Server is a scalable open-source mail server written in Rust with full support for JMAP Core, JMAP Mail, JMAP over WebSocket at IMAP4rev2.[\[16\]](https://en.wikipedia.org/wiki/JSON_Meta_Application_Protocol#cite_note-16)




