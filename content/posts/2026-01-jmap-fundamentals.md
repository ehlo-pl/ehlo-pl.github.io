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

RFC 8620 — JMAP Core
RFC 8621 — JMAP Mail




