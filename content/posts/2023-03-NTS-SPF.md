+++
title = "Note to self - SPF - \"Sender Policy Framework\""
date = 2023-04-01T00:00:00Z
draft = true
description = "Note to self - SPF - \"Sender Policy Framework\""
+++

# SPF - Sender Policy Framework

The Sender Policy Framework (SPF) is an email authentication method designed to prevent email spoofing. Email spoofing is a common malicious practice where the sender's address is forged to appear as if the email is coming from a different source, often used in phishing and spam campaigns.

SPF allows the receiving mail server to check during mail delivery whether the incoming email is authorized by the domain's administrators. It does this by verifying that the email comes from a host authorized by the domain's administrators.

Here's how it works:

1. The domain administrator publishes the SPF record in the Domain Name System (DNS). This record lists all the hosts that are authorized to send email on behalf of the domain.
2. When an email is received, the receiving server extracts the domain from the "envelope from" address (also known as the return-path or MAIL FROM).
3. The receiving server then retrieves the SPF record for the domain from DNS.
4. The server then checks if the IP address of the sender is listed in the SPF record.
5. If the sender's IP is listed in the SPF record, the email passes the SPF check. If not, the email fails the SPF check, which usually results in the email being marked as spam or rejected.

SPF should be used in any scenario where a domain sends email. It's particularly important for businesses and other organizations that send email as part of their regular operations. By implementing SPF, these organizations can help protect their reputation and their recipients from potentially harmful phishing or spam emails. 

An SPF record is a TXT record in a domain's DNS settings that specifies which IP addresses and other mail servers are allowed to send email on behalf of the domain. The structure of an SPF record is as follows:

`v=spf1 [mechanisms] [qualifiers]`

Here's a breakdown of the components:

- `v=spf1`: This is the SPF version tag. It's always at the beginning of the record to identify it as an SPF record.
- `mechanisms`: These define which IP addresses are authorized to send mail. Some common mechanisms include:
    
    - `a`: Mail is allowed from IP addresses resolved by A or AAAA records.
    - `mx`: Mail is allowed from IP addresses resolved by MX records.
    - `ip4:192.0.2.0/24` or `ip6:2001:db8::/32`: Mail is allowed from the specified IPv4 or IPv6 addresses.
    - `include:example.com`: Mail is allowed from IP addresses specified in the SPF record of `example.com`.
    - `all`: This matches everything and is typically used as a catch-all mechanism.
- `qualifiers`: These specify how the mail server should handle mail that matches or does not match the mechanisms. They are optional and include:
    
    - `+` for Pass (default if no qualifier is specified)
    - `-` for Fail
    - `~` for SoftFail
    - `?` for Neutral

Here's an example of an SPF record:

`v=spf1 ip4:192.0.2.0/24 ip4:198.51.100.123 a -all`

This record allows mail from the IP addresses 192.0.2.0/24 and 198.51.100.123, and any IP addresses resolved by A records. Mail from all other IP addresses is not allowed (`-all`).

## Microsoft sources

* [Microsoft 365  Microsoft Defender for Office 365: Set up SPF to help prevent spoofing](https://learn.microsoft.com/en-us/microsoft-365/security/office-365-security/email-authentication-spf-configure?view=o365-worldwide)

## some troubleshooting tools

* [SPF Record Checker spf.myisp.ch](http://spf.myisp.ch)
* DNS looking glasses
	-  https://www.digwebinterface.com/
	-  https://toolbox.googleapps.com/apps/dig/
	- 
  * MS?


## RfC and standards 
* [RfC 7208 Sender Policy Framework (SPF) for Authorizing Use of Domains in Email, Version 1](https://www.rfc-editor.org/rfc/rfc7208)
* [RfC 6376 DomainKeys Identified Mail (DKIM) Signatures](https://www.rfc-editor.org/rfc/rfc6376), 
* [RfC 7489 Domain-based Message Authentication, Reporting, and Conformance (DMARC)](https://www.rfc-editor.org/rfc/rfc7489)
