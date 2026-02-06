+++
date = '2026-02-02T11:40:27+01:00'
draft = true
title = 'Freeipa and Postfix'
+++

Since your machine is already a FreeIPA client with SSSD running, you have a massive head start. Instead of making Postfix and Dovecot talk directly to LDAP (which is a headache with BIND DNs and complex filters), the "clean" way is to leverage **SSSD**.

SSSD handles the caching, offline credentials, and the heavy lifting of LDAP lookups. Here is how to wire them up.

---

## 1. Dovecot Configuration

Dovecot can use PAM for authentication and the system user lookup (via SSSD) for user information.

### PAM Authentication

In `/etc/dovecot/conf.d/10-auth.conf`, ensure you have:

```bash
disable_plaintext_auth = yes
auth_mechanisms = plain login
!include auth-system.conf.ext

```

### Userdb and Passdb

In `/etc/dovecot/conf.d/auth-system.conf.ext`, use `pam` for passwords and `passwd` (which SSSD populates) for user data:

```bash
passdb {
  driver = pam
}

userdb {
  driver = passwd
  # This tells Dovecot to look up the home directory from SSSD
  override_fields = home=/home/fedora/%u
}

```

> **Note:** FreeIPA users usually don't have mail directories created by default. You may need to add `mail_location = maildir:~/Maildir` in `10-mail.conf`.

---

## 2. Postfix Configuration

Postfix needs to know which email addresses are valid. Since SSSD makes FreeIPA users look like local system users, we use `alias` and `local` maps, or LDAP if you want to support virtual aliases.

### Using SSSD/Local Lookups

In `/etc/postfix/main.cf`, ensure Postfix looks at the system database:

```bash
local_recipient_maps = proxy:unix:passwd.byname $alias_maps
mydestination = $myhostname, localhost.$mydomain, localhost, yourdomain.com

```

### Direct LDAP Lookup (Recommended for Aliases)

If you want Postfix to find users by their `mail` attribute in FreeIPA rather than just their username, create a file `/etc/postfix/ldap-users.cf`:

```ini
server_host = ldap://ipa-server.example.com
search_base = cn=users,cn=accounts,dc=example,dc=com
query_filter = (mail=%s)
result_attribute = uid
bind = no

```

*Because the machine is an IPA client, it can often bind via GSSAPI or you can use the host keytab.*

Then add it to `main.cf`:

```bash
virtual_alias_maps = ldap:/etc/postfix/ldap-users.cf

```

---

## 3. SSSD Tweaks

For this to work smoothly, SSSD needs to expose the email attribute. Edit `/etc/sssd/sssd.conf`:

```ini
[domain/example.com]
...
ldap_user_extra_attrs = mail:mail

```

Then restart SSSD: `systemctl restart sssd`.

---

## 4. Permissions & SELinux

Since you are likely on a RHEL/Fedora-based system (given FreeIPA), SELinux might complain about Dovecot reading SSSD pipes or Postfix making network connections.

* **Allow Postfix to talk to LDAP:** `setsebool -P postfix_local_write_mail_spool on` (if using local delivery).
* **Check SSSD permissions:** Ensure the `dovecot` user can access the SSSD private pipe if you aren't using PAM.

---

### The "Pro" Step: Kerberos

Since you're in a FreeIPA environment, you can actually enable **GSSAPI** (Kerberos) for Dovecot and Postfix. This allows users with a valid `kinit` ticket to log into their email without typing a password.

**Would you like me to provide the specific GSSAPI/Keytab configuration steps for Dovecot to enable passwordless Kerberos login?**