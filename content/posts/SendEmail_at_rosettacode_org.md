+++
date = '2026-02-07T00:30:19+01:00'
draft = true
title = 'SendEmail_at_rosettacode_org'
+++

## rosettacode.org

> Rosetta Code is a programming chrestomathy site. The idea is to present solutions to the same task in as many different languages as possible, to demonstrate how languages are similar and different, and to aid a person with a grounding in one approach to a problem in learning another. Rosetta Code currently has 1,340 tasks, 399 draft tasks, and is aware of 986 languages, though we do not (and cannot) have solutions to every task in every language.

And yes, I was curious how my standard task was done for languages which are quite exotic for me. As I remember long time ago I learn on that site that cURL is quite nice SMTP client. :)
Rule for that task is quite simple: 

> *TASK*: 
> Write a function to send an email.
> The function should have parameters for setting From, To and Cc addresses; the Subject, and the message text, and optionally fields for the server name and login details.
> * If appropriate, explain what notifications of problems/success are given.
> * Solutions using libraries or functions from the language are preferred, but failing that, external programs can be used with an explanation.
> * Note how portable the solution given is between operating systems when multi-OS languages are used.

For most languages it was done in the simplest way, without authentication. only 12 (contrary 58 total) examples uses 587/tcp. And it's quite funny see some basic action done on such different ways. It's quite funny that both that examples, nor standard email libraries from vendors ignore some basic assumption (i.e. if mail server answer with some code 4xy - then react in specific way, how to handle codes 500). 

## References

<https://rosettacode.org/wiki/Send_email>
