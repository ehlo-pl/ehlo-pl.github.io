+++
date = '2026-07-07T03:17:30+02:00'
draft = true
title = 'Microsoft Graph API and Eventual Consistency'
description = "The ConsistencyLevel: eventual header does nothing for mailbox queries - the real Graph eventual consistency problem is a successful, empty search result right after sending"
tags = ["microsoft-graph", "exchange-online", "microsoft-365", "golang", "eventual-consistency", "odata", "gomailtesttool"]
categories = ["Microsoft 365"]
+++

## The Discovery

I wanted my [gomailtesttool](https://github.com/ehlo-pl/gomailtesttool) to "properly handle
eventual consistency" on the Graph API. If you ever googled that phrase, you already know
what comes up first: the famous `ConsistencyLevel: eventual` header. Every second
StackOverflow answer about Graph queries tells you to add it. So my first instinct was the
same — go through all the Graph calls in the tool and add the header where it belongs.

The surprise: it belongs *nowhere* in my code. And the actual eventual consistency problem
I had was a completely different one, hiding in a place where no header can help.

## What Everyone Means by "Eventual Consistency" in Graph

The documented story is about **advanced queries on directory objects** — users, groups,
applications, and other Entra ID (Azure AD) objects. The directory keeps a separate index
for the fancy query capabilities, and that index is eventually consistent with the main
store. So when you want things like:

- `$count` as a URL segment or query parameter,
- `$search` on users or groups,
- `$filter` with operators like `endsWith`, or `$filter` on some specific properties,
- `$orderby` combined with `$filter`,

...Graph requires you to opt in to that index explicitly:

```text
GET https://graph.microsoft.com/v1.0/users?$filter=endsWith(mail,'@ehlo.pl')&$count=true
ConsistencyLevel: eventual
```

Both parts are mandatory — the header *and* `$count=true`. Forget one of them and you get
`Request_UnsupportedQuery` or just wrong results. This is all in the
[advanced query capabilities](https://learn.microsoft.com/en-us/graph/aad-advanced-queries)
doc, and it is real and important — *if you query the directory*.

## Where the Header Does Nothing

Here is the part which I did not see spelled out clearly anywhere. Graph serves (at least)
two very different backends behind one API surface:

| Query | Backend | Needs `ConsistencyLevel`? |
|-------|---------|--------------------------|
| `/users?$filter=...&$count=true` | Entra ID directory | **Yes** — with `$count=true` |
| `/users/{mailbox}/messages?$filter=...` | That user's Exchange Online mailbox | **No** |
| `/users/{mailbox}/events`, `/calendar/getSchedule` | Exchange Online | **No** |

In the second and third row, the `{mailbox}` part is just a routing key. Graph resolves
which mailbox to talk to and then the query runs *inside* Exchange Online, against mailbox
data. The directory index — the whole reason the header exists — is not involved at all.

I went through every Graph call in gomailtesttool: `sendmail`, `getinbox`, `getevents`,
`getschedule`, `searchandexport`, `exportmessages`... All of them are
`client.Users().ByUserId(mailbox).Something()`. Not a single directory query. Adding
`ConsistencyLevel: eventual` to those requests would be pure cargo cult — Graph would
ignore it.

So: task done, nothing to do? Not really.

## The Real Eventual Consistency Problem

gomailtesttool is a mail flow testing tool. A typical test scenario is: send a message
through Graph, then immediately search for it to confirm delivery:

```powershell
gomailtest msgraph sendmail --to "probe@ehlo.pl" --subject "flow test"
gomailtest msgraph exportmessages --subject "flow test"
```

And here Exchange Online *is* eventually consistent, just in its own way. A message that
was delivered a second ago may not be visible yet to a `$filter` query — indexing takes a
moment. What does Graph return in that window? Not an error. Not a 404. A perfectly
healthy `200 OK` with an empty `value: []`.

That empty success is the trap. My tool already had proper retry logic — exponential
backoff, honoring `Retry-After` on 429, retrying 503/504, all by the
[throttling guidance](https://learn.microsoft.com/en-us/graph/throttling). But all of that
triggers on *errors*. An empty result set is a success, so the retry loop happily accepted
it on the first attempt and the tool reported "no messages found" — for a message that
would show up two seconds later.

## The Fix: Treat "Empty" as Transient

The fix is conceptually simple: for search operations where the message is *expected* to
exist, a successful-but-empty response should be retried like a transient error. In Go I
did it with a sentinel error, so the existing retry machinery could stay untouched:

```go
// errResultNotYetVisible signals that a mailbox query succeeded but returned
// no messages. Graph is eventually consistent: a just-sent message may not be
// indexed yet, so this condition is retried like a transient error.
var errResultNotYetVisible = errors.New("no messages matched the filter (message may not be indexed yet)")

func isRetryableGraphErrorOrEmptyResult(err error) (bool, time.Duration) {
	if errors.Is(err, errResultNotYetVisible) {
		return true, 0
	}
	return isRetryableGraphError(err) // 429/503/504 + Retry-After, as before
}
```

The fetch itself goes through a small helper. The operation closure returns the sentinel
when the result set is empty, the classifier marks it retryable, and after the retries are
exhausted the sentinel is swallowed — because "the message really is not there" must stay
a normal, non-error outcome:

```go
func fetchMessagesWithRetry(ctx context.Context, maxRetries int, baseDelay time.Duration,
	operation string, fetch func() ([]models.Messageable, error)) ([]models.Messageable, error) {

	var messages []models.Messageable
	attempt := 0
	err := retry.RetryWithBackoffFunc(ctx, maxRetries, baseDelay, func() error {
		attempt++
		result, apiErr := fetch()
		if apiErr != nil {
			return apiErr
		}
		messages = result
		if len(messages) == 0 && attempt <= maxRetries {
			log.Printf("[INFO] %s: no matching messages yet (attempt %d/%d); message may not be indexed yet, retrying...",
				operation, attempt, maxRetries+1)
			return errResultNotYetVisible
		}
		return nil
	}, isRetryableGraphErrorOrEmptyResult)

	if errors.Is(err, errResultNotYetVisible) {
		return nil, nil // retries exhausted, still empty: caller reports not-found as before
	}
	if err != nil {
		return nil, err
	}
	return messages, nil
}
```

The handler side barely changed — the SDK call just moved into the injected closure:

```go
messages, err := fetchMessagesWithRetry(ctx, config.MaxRetries, config.RetryDelay,
	"searchAndExport", func() ([]models.Messageable, error) {
		apiResult, apiErr := client.Users().ByUserId(mailbox).Messages().Get(ctx, requestConfig)
		if apiErr != nil {
			return nil, apiErr
		}
		return apiResult.GetValue(), nil
	})
```

One detail I liked: the `attempt <= maxRetries` guard means the *final* attempt returns
nil on empty instead of the sentinel, so the retry loop does not log a scary "operation
failed after 3 retries" for what is an ordinary not-found. And with `--maxretries 0` the
whole thing degrades to a single attempt — the old behavior, one flag away.

## The Trade-Offs

Nothing is free, of course:

- **A genuinely missing message now takes longer to report.** With my defaults (3 retries,
  2 s base delay, doubling) that is about 2+4+8 = 14 seconds of waiting before "no
  messages found". For a test tool this is fine — I *want* it to wait out the indexing
  delay — but it would be wrong default for an interactive app.
- **Not every empty result is transient.** I applied this only to `searchandexport` and
  `exportmessages`, where the caller searches for one specific message that should exist.
  For `getinbox` or `getevents` an empty list is a legitimate final answer — retrying an
  empty inbox would be nonsense.
- **Context cancellation must not be swallowed.** Ctrl+C during the backoff wait has to
  come out as an error, not as a polite "message not found". The sentinel check with
  `errors.Is` takes care of that, since the cancellation error is a different one.

Testing was surprisingly pleasant: because the Graph SDK client is hidden behind the
`fetch` closure, the retry logic tests need no mocking framework at all — the test just
hands in a closure that returns empty twice and a message on the third call.

> **NEEDS YOUR LAB:** a `--verbose` capture of `exportmessages` running right after
> `sendmail` against the real tenant, showing one or two
> `[INFO] exportMessages: no matching messages yet (attempt 1/4)` lines before the
> successful export — to show the indexing delay is real, not theoretical.

## Why This Matters

If you take one thing from this post: **"eventual consistency" in Graph is two unrelated
problems**, and the popular fix addresses only one of them.

1. Directory queries (`/users`, `/groups`, ...) with advanced query features → add
   `ConsistencyLevel: eventual` + `$count=true`. Documented everywhere.
2. Mailbox queries right after a write → no header will help you. You have to poll:
   retry the successful-but-empty response with backoff, and decide carefully *which*
   operations deserve it.

The second one is sneakier because nothing fails. There is no error code to catch, no
exception to log — just a correct-looking empty array which is a lie for the next few
seconds.

## Closing Thought

What was funny — I started this change fully convinced I will be adding a header, and
ended up explicitly *not* adding it, with a note in the docs why it is absent. That is
maybe the best kind of fix: the investigation was worth more than the code. The whole
change is a sentinel error, one helper function and one classifier wrapper; the hard part
was realizing which eventual consistency I actually had.

## References

- [Advanced query capabilities on Microsoft Entra ID objects](https://learn.microsoft.com/en-us/graph/aad-advanced-queries) — when `ConsistencyLevel: eventual` is actually required
- [Microsoft Graph throttling guidance](https://learn.microsoft.com/en-us/graph/throttling) — 429/Retry-After handling
- [gomailtesttool](https://github.com/ehlo-pl/gomailtesttool) — the tool this change landed in (v3.5.1)
- [msgraph-sdk-go](https://github.com/microsoftgraph/msgraph-sdk-go) — the Kiota-generated Go SDK used for all Graph calls
