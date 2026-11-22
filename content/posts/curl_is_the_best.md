+++
title = "Curl is the best (also on Windows)"
date = 2019-07-01T00:00:00Z
draft = false
description = "curl.exe ships with Windows 10 and is built with Schannel, so it checks certificates against the Windows certificate store. No more -k for internal CAs."
categories = ["Scripting", "PowerShell"]
tags = ["curl", "windows", "powershell", "schannel", "tls", "x509", "certificates"]
+++

## The Discovery

Curl is also on Windows. And I don't mean only the build downloaded from the curl project
site. There is also one **provided by Microsoft**, and that one uses Microsoft's own TLS
library, Schannel.

Daniel Stenberg (the curl author) wrote about it back in January 2018:

> since insider build 17063 of Windows 10, curl is now a default component.

via: [Microsoft curls too](https://daniel.haxx.se/blog/2018/01/13/microsoft-curls-too/)

I don't know how I could overlook it. OK, my excuse: I usually work on machines older than
Windows 10, mostly servers. And of course it works outside of
[WSL aka Windows Subsystem for Linux](https://learn.microsoft.com/en-us/windows/wsl/install).
It is a native Windows binary, `C:\Windows\System32\curl.exe`, and it runs straight from
cmd or PowerShell.

## What Microsoft Shipped

Microsoft announced it on the command line blog
([Tar and Curl Come to Windows!](https://devblogs.microsoft.com/commandline/tar-and-curl-come-to-windows/),
Rich Turner, January 2018). Windows 10 Insider build 17063 and later include "the real-deal
`curl` and `tar` executables". For everyone else it came with Windows 10 version 1803.

Some details from Daniel's post are worth knowing:

- Microsoft builds and ships it **independently** of the curl project. The first one was 7.55.1,
  while 7.57.0 was already the latest upstream release.
- It is built with the **WinSSL (Schannel)** TLS backend, not OpenSSL.
- At that time there was no HTTP/2 and no IDN support.

So it is real curl, but not exactly the same curl as the one from curl.se. To check which
one is on the box:

```powershell
curl.exe --version
```

The first line shows the curl version and the TLS library it was built with (Schannel or
OpenSSL).
 

### PowerShell trap: `curl` is not curl

In Windows PowerShell 5.1, `curl` is a built-in **alias for `Invoke-WebRequest`**. It shadows
`curl.exe` and takes completely different parameters. So `curl -v https://...` in Windows
PowerShell runs a cmdlet, not curl. So I call it with the extension:

```powershell
curl.exe -v https://blog.ehlo.pl/
```

Or remove the alias for the session with `Remove-Item Alias:curl`. PowerShell 7+ does not define
this alias anymore, but I just type `curl.exe` everywhere. It works in both, and in scripts it is
clear what runs.

## Certificates: stop using `-k`

This is the part I like most.

How many times I have seen `curl -k` in a runbook, because the server has a certificate from
an internal CA? Too many. `-k` (`--insecure`) switches off certificate
verification completely, and the curl man page says it directly: "using this option makes the
transfer insecure". Worth to carry on avoiding it.

How curl finds trusted CAs depends on the TLS backend it was built with.

### curl.se build (OpenSSL)

The official Windows build is based on OpenSSL and, by default, does not read the Windows
certificate store. Instead it looks for a CA bundle file named `curl-ca-bundle.crt`. According
to [SSL Certificate Verification](https://curl.se/docs/sslcerts.html), on Windows curl searches
these places, in this order:

1. the application's directory (where `curl.exe` is)
2. the current working directory
3. the Windows System directory (e.g. `C:\Windows\System32`)
4. the Windows directory (e.g. `C:\Windows`)
5. all directories along `%PATH%`

So the simple fix for an internal CA: append the root CA certificate (PEM) to
`curl-ca-bundle.crt` next to `curl.exe`. Other options:

- `--cacert <file>` points to a CA bundle for one call.
- The `CURL_CA_BUNDLE` environment variable does the same for every call (it is ignored when the
  TLS backend is Schannel).
- `--ca-native` (curl 8.2.0 and later) tells an OpenSSL build on Windows to load the certificates
  from the Windows "CA" and "ROOT" stores. Back in 2019 this option did not exist, and this was
  exactly the thing I was missing.

```powershell
# OpenSSL build of curl, internal CA in a PEM file
curl.exe --cacert C:\certs\internal-root-ca.pem -v https://mail.contoso.internal/owa/

# OpenSSL build of curl 8.2.0+, trust what Windows trusts
curl.exe --ca-native -v https://mail.contoso.internal/owa/
```

### Microsoft build (Schannel)

On the Microsoft-released version there is no bundle to maintain:

> If curl was built with Schannel, then curl uses the certificates that are built into the OS.

So if the internal root CA is already deployed to the machine (GPO, Intune, by hand,
whatever), the in-box `curl.exe` simply trusts it. No `-k`, no extra files. Nice. :)
(`--ca-native` has no effect for Schannel; it already uses the OS store.)

One thing that surprised me: **Schannel also checks certificate revocation** ("Schannel runs
CRL checks on certificates unless peer verification is disabled"). With an internal PKI where
the CRL distribution point is not reachable from the test box, the connection fails
even if the chain itself is fine. Instead of going back to `-k`, there are two Schannel-only
options:

- `--ssl-revoke-best-effort` (7.70.0+): ignore revocation check failures caused by missing or
  offline distribution points. Still checks the chain and the name.
- `--ssl-no-revoke`: disable revocation checks entirely.

The first one is the better choice. And in fact this failure is useful information: if curl
can't reach the CRL, probably some other client can't too.

## Some Examples

My original note had only this:

```powershell
curl.exe -k -vvv https://site.to.verify.certs/
```

which, now I look at it, is a bit funny: `-k` means curl does *not* verify the certificate. For
checking certificates, drop the `-k` and let curl complain:

```powershell
curl.exe -v https://site.to.verify.certs/
```

With `-v` curl prints the TLS handshake details, and if verification fails it stops with an
error instead of quietly continuing.

Only headers, no body:

```powershell
curl.exe -I https://site.to.verify.certs/
```

Test one specific server behind a load balancer, but keep the real host name for SNI and
certificate verification. This one is great for checking that every node in an Exchange or mail
gateway farm has the right certificate:

```powershell
curl.exe -v --connect-to mail.contoso.com:443:10.0.0.21:443 https://mail.contoso.com/owa/
```

From the man page: `--connect-to` "does NOT affect the hostname/port number that is used for
TLS/SSL (e.g. SNI, certificate verification)". So the certificate is verified against
`mail.contoso.com`, but the TCP connection goes to `10.0.0.21`.

## Why This Matters

- **It is already there.** On Windows 10 1803 or newer, HTTPS endpoints can be tested without
  installing anything. Very useful on servers where I can't (or shouldn't)
  install tools.
- **It trusts what Windows trusts.** The Schannel build gives the same trust decision as other
  Windows clients on that machine. If curl says the certificate is bad, other Schannel-based
  clients on that box will most likely have a problem too.
- **No more `-k` in scripts.** Either deploy the CA to the Windows store (Schannel build), or add
  it to `curl-ca-bundle.crt` / use `--ca-native` (OpenSSL build).

When not: the in-box build follows Windows updates, not curl releases, so it is usually behind
upstream and has fewer features. If I need something new, I take the curl.se build, and then
the OpenSSL CA rules from above apply.

## Closing Thought

Curl is the best. That it now comes with Windows, and uses the Windows certificate store, made
my life on Windows servers much easier. Only remember: on Windows PowerShell type `curl.exe`,
not `curl`.

HTH,

Ziemek :)

## References

- [Microsoft curls too](https://daniel.haxx.se/blog/2018/01/13/microsoft-curls-too/) (Daniel Stenberg, January 2018)
- [Tar and Curl Come to Windows!](https://devblogs.microsoft.com/commandline/tar-and-curl-come-to-windows/) (Rich Turner, Sr. Program Manager, Windows Console & Command-Line)
- [curl on Windows](https://learn.microsoft.com/windows/curl/) (Microsoft Learn)
- [SSL Certificate Verification](https://curl.se/docs/sslcerts.html) (curl.se)
- [curl man page](https://curl.se/docs/manpage.html)
