+++
title = "note to self - how to send simple mail to Exchange using EWS and Windows PowerShell"
date = 2023-06-01T00:00:00Z
draft = true
description = "note to self - how to send simple mail to Exchange using EWS and Windows PowerShell"
categories = ["Scripting", "PowerShell"]
tags = ["Scripting", "PowerShell", "GraphAPI"]
+++



```powershell

$Mailsender = 'MeganB@vdv22.eu'
$TenantId = '27267ede-acb6-4c35-9e70-20e6e84f6e35'
$MailRecipient = $Mailsender
<#---------------------------------------------
Install-Module Microsoft.Graph.Authentication -Scope CurrentUser
Install-Module Microsoft.Graph.Mail -Scope CurrentUser
Install-Module Microsoft.Graph.Users.Actions -Scope CurrentUser #>
#---------------------------------------------

Connect-MgGraph -TenantId $tenantId -Scope "Mail.Send, Mail.ReadWrite"
$Details = Get-MgContext
$Details
#----------------------------------------------

#region craftig an e-mail
$SendingDateTime = "{0:G}" -f (Get-Date)
$MessageBody = @{
    content = "This Mail is sent via MSGraph Comandlets at $sendingDateTime"
    contentType = 'HTML'
}
$MailSender = $details.Account
$recipient = @{
                emailAddress = @{
                    address = $MailRecipient 
                }
            }
#endregion

#region Sending the e-mail
$NewMessage = New-MguserMessage -UserId $Mailsender -Body $MessageBody -ToRecipients $recipient -Subject 'MS Graph Testmail'
Send-MgUserMessage -UserId $MailSender -Messageid $newmessage.id
#endregion


```


 

## References 

- [some chatgtp advise](https://chat.openai.com/share/2696a00a-bc45-486d-a01d-efa1861eab9b])

## See also: 

- [mailozaurr](https://github.com/EvotecIT/Mailozaurr)
- [everything.curl.dev/usingcurl/smtp](https://everything.curl.dev/usingcurl/smtp)
- https://www.powershell.co.at/send-an-e-mail-using-the-ms-graph-powershell-commandlets-in-3-step