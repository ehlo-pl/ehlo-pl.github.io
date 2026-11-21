+++
date = '2026-07-28T00:23:51+02:00'
draft = true
title = 'Logparser.exe_in_2026'
description = "Microsoft Log Parser 2.2 is two decades old and still the fastest way I know to run SQL over mail, IIS and Windows logs"
tags = ["logparser", "logs", "windows", "iis", "exchange", "troubleshooting"]
categories = ["Tools"]
+++

## The Discovery

Every time I have a few hundred megabytes of logs and no SIEM in sight, I end up with the same small tool: `LogParser.exe`. It is old. Really old — the download page for [Log Parser 2.2](https://www.microsoft.com/en-us/download/details.aspx?id=24659) still lists Windows XP, Windows 2000 and Windows Server 2003 as system requirements. And still, in 2026, I did not find anything that gets me from "a pile of files" to "an answer" faster.

> **NEEDS YOUR LAB:** the real story — which case made you reach for logparser again (mail flow? IIS? Exchange message tracking?). One or two sentences in your own words go here.

## What Is Log Parser?

Microsoft describes it as a tool that "provides universal query access to text-based data such as log files, XML files and CSV files", plus key data sources on Windows like Event Log, Registry, file system and Active Directory. The idea is simple: you write a SQL-like query, pick an input format and an output format, and the engine does the rest.

Three pieces to remember:

- **Input formats** — IIS logs (all flavours), W3C, NCSA, CSV, TSV, XML, plain text lines, Event Log (`EVT`), file system, registry, Active Directory, NetMon captures, ETW traces. Version 2.2 also has a COM input format, so you can plug in your own parser.
- **Output formats** — CSV, TSV, XML, W3C, IIS, custom templates, on-screen text (`NAT`) and `DATAGRID`, SQL and SYSLOG targets, and `CHART`, which renders an image.
- **The query** — `SELECT`, `WHERE`, `GROUP BY`, `ORDER BY`, `TOP`, aggregate functions like `COUNT(*)`, and a set of string and date functions.

The count of formats differs a bit between sources, so I do not put a hard number here.

## How It Works

The basic command line has this shape:

```powershell
LogParser.exe -i:<input format> -o:<output format> "<query>"
```

For example, the ten most frequent event IDs in the local System log, printed to the console:

```powershell
LogParser.exe -i:EVT -o:NAT "SELECT TOP 10 EventID, COUNT(*) AS Hits FROM System GROUP BY EventID ORDER BY Hits DESC"
```

The same idea works on any CSV-like file — the file name in `FROM` is simply the path:

```powershell
LogParser.exe -i:CSV -o:DATAGRID "SELECT TOP 20 * FROM C:\logs\export.csv"
```

> **NEEDS YOUR LAB:** real output of the first query from the lab machine (screenshot or pasted `NAT` output), saved as `assets/logparser-evt-top10.png`.

Because the engine is a COM component (`logparser.dll`), you can also call it from PowerShell or scripts instead of the command line. I did not test this in the lab yet, so no example here.

> **NEEDS YOUR LAB:** one working example with real mail logs — for me the natural candidate is Exchange message tracking logs or Postfix `mail.log` through `-i:TEXTLINE`. Needs the real file layout, the real query and the real result, I will not guess the columns.

## Log Parser Studio

There is also a GUI: [Log Parser Studio](https://techcommunity.microsoft.com/t5/Exchange-Team-Blog/Introducing-Log-Parser-Studio/ba-p/601131), published by the Exchange team. It is a front-end, not a replacement — it needs Log Parser 2.2 installed, because it uses `logparser.dll`. Version 1.0 exposed only part of the formats; according to the [2.0 announcement](https://techcommunity.microsoft.com/blog/exchange/log-parser-studio-2-0-is-now-available/593266) all input and output formats got at least preliminary support there. Good for keeping a library of saved queries.

## Why This Matters

- No server, no index, no ingestion pipeline. Copy the files, run a query.
- SQL is something most admins already know, so the learning curve is small.
- It is a single download, which matters on locked-down servers where I cannot install anything bigger.

What I would keep in mind:

- It is a 32-bit-era tool from the Windows Server 2003 age. Nothing new is expected from it.
- Whole-file parsing is fine for hundreds of megabytes; for continuous monitoring or many hosts it is the wrong tool, a real log platform does that better.
- Treat the downloaded installer like any other binary — get it only from the official Microsoft page.

> **NEEDS YOUR LAB:** whether it still runs cleanly on Windows 11 / Windows Server 2025 in your lab, and any quirks you hit.

## Closing Thought

Honestly it feels slightly funny that the best answer to "grep is not enough" is a tool older than most of the libraries I use daily. But the combination of SQL and zero setup is hard to beat for one-off investigations.

> **NEEDS YOUR LAB:** your own opinion and what I want to try next (alternatives? a Go or PowerShell clone?).

## References

- [Log Parser 2.2 — Microsoft Download Center](https://www.microsoft.com/en-us/download/details.aspx?id=24659)
- [What's New in Log Parser 2.2 — Microsoft Learn / TechNet](https://technet.microsoft.com/library/ee692660.aspx)
- [Introducing Log Parser Studio — Exchange Team Blog](https://techcommunity.microsoft.com/t5/Exchange-Team-Blog/Introducing-Log-Parser-Studio/ba-p/601131)
- [Log Parser Studio 2.0 is now available — Exchange Team Blog](https://techcommunity.microsoft.com/blog/exchange/log-parser-studio-2-0-is-now-available/593266)
