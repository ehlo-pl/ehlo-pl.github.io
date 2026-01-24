+++
title = "how to send simple mail to Exchange using EWS and Windows PowerShell"
date = 2023-06-01T00:00:00Z
draft = true
description = "how to send simple mail to Exchange using EWS and Windows PowerShell"
categories = ["Scripting", "PowerShell"]
tags = ["Scripting", "PowerShell", "EWS", "sendmail"]
+++





Please use that basic code: 
```powershell
# Load the EWS Managed API assembly
Add-Type -Path "C:\Program Files\Microsoft\Exchange\Web Services\2.2\Microsoft.Exchange.WebServices.dll"

# Set the credentials for Exchange Online
$credentials = New-Object Microsoft.Exchange.WebServices.Data.WebCredentials("your-email@example.com", "your-password")

# Create the Exchange service object
$service = New-Object Microsoft.Exchange.WebServices.Data.ExchangeService([Microsoft.Exchange.WebServices.Data.ExchangeVersion]::Exchange2013_SP1)
$service.Credentials = $credentials

# Specify the Exchange Online endpoint URL
$service.Url = New-Object Uri("https://outlook.office365.com/EWS/Exchange.asmx")

# Create the email message
$message = New-Object Microsoft.Exchange.WebServices.Data.EmailMessage($service)
$message.Subject = "Test Email"
$message.Body = "This is a test email sent via EWS."

# Set the recipient email address
$message.ToRecipients.Add("recipient@example.com")

# Send the email
$message.SendAndSaveCopy()

Write-Host "Email sent successfully."
```
To use this script, make sure you have the EWS Managed API assembly (Microsoft.Exchange.WebServices.dll) installed on your machine. Adjust the path in the Add-Type line to the correct location if necessary.

Replace "your-email@example.com" and "your-password" with your actual Exchange Online email address and password, respectively.

Set the desired subject, body, and recipient email address by modifying the appropriate lines in the script.

After executing the script, it will send the email and display a success message in the console.

Please note that this script assumes you have the necessary permissions to send emails on behalf of the specified account in Exchange Online.

The same for on premises will be very similar: 
```powershell
# Load the EWS Managed API assembly
Add-Type -Path "C:\Program Files\Microsoft\Exchange\Web Services\2.2\Microsoft.Exchange.WebServices.dll"

# Set the credentials for Exchange on-premises
$credentials = New-Object Microsoft.Exchange.WebServices.Data.WebCredentials("your-username", "your-password", "your-domain")

# Create the Exchange service object
$service = New-Object Microsoft.Exchange.WebServices.Data.ExchangeService([Microsoft.Exchange.WebServices.Data.ExchangeVersion]::Exchange2013_SP1)
$service.Credentials = $credentials

# Specify the Exchange on-premises endpoint URL
$service.Url = New-Object Uri("https://your-exchange-server/EWS/Exchange.asmx")

# Create the email message
$message = New-Object Microsoft.Exchange.WebServices.Data.EmailMessage($service)
$message.Subject = "Test Email"
$message.Body = "This is a test email sent via EWS."

# Set the recipient email address
$message.ToRecipients.Add("recipient@example.com")

# Attach a file
$attachmentPath = "C:\path\to\attachment.txt"
$attachment = New-Object Microsoft.Exchange.WebServices.Data.FileAttachment($attachmentPath)
$attachment.Name = (Get-Item $attachmentPath).Name
$message.Attachments.Add($attachment)

# Send the email
$message.SendAndSaveCopy()

Write-Host "Email sent successfully."
```
Please note that this script assumes you have the necessary permissions to send emails on behalf of the specified account in Exchange 2019 on-premises. Additionally, ensure that you replace "https://your-exchange-server" with the actual URL of your Exchange server.

Finally it should be something like that [scripts/__fx__Send-EmailViaEWS.ps1](scripts/__fx__Send-EmailViaEWS.ps1) build in function. 

## See also: 

- Przemek Kłys - [mailozaurr](https://github.com/EvotecIT/Mailozaurr) and of course as module https://www.powershellgallery.com/packages/mailozaurr
- Bartek Bielawski EWS module - [github.com/bielawb/EWS](https://github.com/bielawb/EWS) and of course as module https://www.powershellgallery.com/packages/EWS/ 4
- 