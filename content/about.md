# Modern e-mail solutions blog – about-me

Hello, I'm Ziemek Borowski, and I used to be the postmaster.

I have quite extensive experience as an e-mail technical administrator for large organizations. Let's call me myself ``postmaster``. But mostly based on proprietary solution – to say direct – MS Exchange Server and ancestor – M365 Exchange Online. I worked also with Google Workspace or (in past) Lotus/IBM/HCL Domino/Notes. I had some experience with open source, but it was on production years ago (20-ish). I decided to explore some alternative approaches in many different directions and report here, on that yet-another-technical-blog my concerns and findings.

I have some ideas to explore:

- some standard commodity which I know, but not enough explore. Some examples? There are:
  - postfix as on-premises mail submission / relay for [LoB](https://en.wikipedia.org/wiki/Line_of_business) applications (sending sometimes to regular e-mail organization, sometimes to external smart-hosts)
  - postfix as build from scratch, not ready to go mail site (yeah, trivial, but bless and horror of open source is - every build it in own way). Yes, there are https://www.iredmail.org/ or https://modoboa.org/en/features/ - but I want back to roots and look under the hood.
- explore new mail organization solutions - mostly open-sources. Some initial examples:
    - [WildDuck email server](https://docs.wildduck.email/) - but it also include i.e. [ZoneMTA](https://github.com/zone-eu/zone-mta) and [Haraka](http://haraka.github.io/) to validate recipient addresses and quota usage against the WildDuck users database and to store/filter messages.
    - [ANCT](https://anct.gouv.fr/), a French government agency project [Messages](https://github.com/suitenumerique/messages)
    - [stalwart] (https://github.com/stalwartlabs/stalwart) - All-in-one Mail & Collaboration server. Secure, scalable and fluent in every protocol (IMAP, JMAP, SMTP, CalDAV, CardDAV, WebDAV).
    - 
- explore new tools for "spammers" - organization which have to send
    - kumomta 
- email related evens which I participated or just only observed/know
- email related books - less on technical details but more on some common fundamentals
- some both encyclopedic and simple how-to try of protocols and tools - both classical like SMTP, IMAP, DNS, SPF, DKIM, DMARC but also on that new like JMAP
