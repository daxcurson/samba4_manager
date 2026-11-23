# Automated installation with Ansible

This directory has an Ansible playbook that installs Samba4 Manager on a Samba
AD domain controller, or updates an existing install. Running it again is safe:
it only changes what is out of date.

## What it sets up

```
browser ──HTTPS──▶ Apache (:443) ──HTTP──▶ waitress (127.0.0.1:6543) ──ldap://localhost──▶ Samba AD DC
                   reverse proxy            systemd service "samba4_manager",
                                            runs as the unprivileged user samba4mgr
```

| Item | Location |
|---|---|
| Application source (git checkout) | `/opt/samba4_manager/src` |
| Python virtualenv | `/opt/samba4_manager/venv` |
| Application configuration | `/etc/samba4_manager/production.ini` |
| Cookie secrets (generated on first run) | `/etc/samba4_manager/session_secret`, `auth_secret` |
| systemd unit | `/etc/systemd/system/samba4_manager.service` |
| Apache configuration | `/etc/httpd/conf.d/samba4_manager.conf` (Fedora/RHEL) or `/etc/apache2/sites-available/samba4_manager.conf` (Debian/Ubuntu) |
| Logs | `journalctl -u samba4_manager`, plus `samba4_manager_*.log` in the Apache log directory |

The application does not run as root. It logs in to Samba over
`ldap://localhost` with the user name and password typed on the login page.

## Supported distributions

| Family | Tested | Notes |
|---|---|---|
| Debian / Ubuntu | Ubuntu 24.04, in a container without systemd (the service unit itself was not exercised) | Installs `python3-samba`, `apache2` |
| Fedora | not yet | Installs `python3-samba`, `python3-samba-dc`, `httpd`, `mod_ssl`; handles SELinux and firewalld |
| RHEL, Rocky, AlmaLinux | not yet | These do not ship a Samba AD DC; see [Samba built from source](#samba-built-from-source) |

To support another distribution, add `roles/samba4_manager/vars/<os_family>.yml`
modelled on `Debian.yml`. The playbook tells you which file name it looked for.

## Requirements

- **On the server:** a working Samba AD DC and SSH access with `sudo` (or root).
  The playbook installs everything else, including Apache and git.
- **On the machine you run it from:** Ansible (`ansible-core` 2.14 or later is
  enough, no extra collections). You can also run it on the server itself.

## Usage

1. Create your inventory:

   ```bash
   cd deploy
   cp inventory.example.ini inventory.ini
   ```

   Edit `inventory.ini`: put your domain controller's host name under
   `[samba4_manager]` and set any variables you need (see below).
   `inventory.ini` is ignored by git.

2. Run the playbook:

   ```bash
   ansible-playbook site.yml --ask-become-pass
   ```

   To install on the machine you are logged into, use
   `localhost ansible_connection=local` as the host in `inventory.ini`.

3. Open `https://<server_name>/samba4_manager/` and log in with a domain
   administrator account. Until the PCs trust the internal CA (see
   [Trusting the certificate](#trusting-the-certificate)), the browser warns
   about the certificate.

To **update** to a newer version, run the same command again. Set
`samba4_manager_version` to a tag or commit to pin a release.

## Variables

All variables and their defaults are in
[`roles/samba4_manager/defaults/main.yml`](roles/samba4_manager/defaults/main.yml).
These are the ones you are most likely to change:

| Variable | Default | Purpose |
|---|---|---|
| `samba4_manager_server_name` | the host's FQDN | Name users type in the browser |
| `samba4_manager_url_path` | `/samba4_manager` | URL path; use `/` to publish at the site root |
| `samba4_manager_version` | `master` | Branch, tag or commit to deploy |
| `samba4_manager_git_repo` | this repository on GitHub | Use your own fork or mirror |
| `samba4_manager_tls_cert`, `samba4_manager_tls_key` | empty (use the internal CA) | Paths to your own certificate and key on the server |
| `samba4_manager_ca_permitted_domain` | domain part of `samba4_manager_server_name` | The only domain (and its subdomains) the internal CA can sign for |
| `samba4_manager_tls_selfsigned_days`, `samba4_manager_tls_renew_days` | `825`, `30` | Validity of the server certificate, and how many days before expiry the playbook renews it |
| `samba4_manager_port` | `6543` | Local port the application listens on |
| `samba4_manager_manage_firewall` | `true` | Open HTTP/HTTPS in firewalld if it is running |
| `samba4_manager_selinux_allow_proxy` | `true` | Enable `httpd_can_network_connect` so Apache can reach the app |
| `samba4_manager_session_timeout_minutes` | `30` | Inactivity time after which users must log in again |
| `samba4_manager_admin_group_sids` | `[S-1-5-32-544]` (BUILTIN\\Administrators) | Groups whose members may log in; nested membership counts |
| `samba4_manager_log_level` | `WARN` | Application log level |

## Things to know

- **Python version.** The Samba bindings only work with the Python
  version the distribution built them for. The playbook finds that
  interpreter automatically. It also rebuilds the virtualenv when that
  interpreter changes, for example after a Fedora release upgrade.
- **HTTPS certificate.** Unless you give your own certificate, the playbook
  creates an internal certificate authority (CA). That CA signs the server
  certificate. See [Trusting the certificate](#trusting-the-certificate).
- **Port 80.** If no other virtual host exists, the HTTP-to-HTTPS virtual
  host becomes Apache's default for port 80. It only redirects the
  application path, so other content on port 80 keeps working.
- **Logins and restarts.** Each session keeps its user's credentials in the
  application's memory only; the browser just gets a random token. So
  restarting the service (which the playbook does when it updates the app)
  logs everyone out.
- **Secrets.** Cookie secrets are generated on the server and never leave it.
  To manage them yourself, set `samba4_manager_session_secret` and
  `samba4_manager_auth_secret`, ideally with Ansible Vault.

### Samba built from source

Set `samba4_manager_samba_python_packages: []` so that no distribution
packages are installed. Then set `samba4_manager_python` to an interpreter
that can `import samba`. If the bindings live outside that interpreter's
default path (for example under `/usr/local/samba`), make them importable
first. One way is a `.pth` file in that interpreter's `site-packages`.

## Trusting the certificate

On the first run the playbook creates an internal CA. Its certificate is at
`/etc/pki/tls/certs/samba4_manager-ca.crt` on Fedora/RHEL, or
`/etc/ssl/certs/samba4_manager-ca.crt` on Debian/Ubuntu. Import it once into
the "Trusted Root Certification Authorities" of the PCs that use the app, and
browsers stop warning.

- **The CA is valid for 10 years.** The server certificate it signs is renewed
  by the playbook, 30 days before it expires, so the PCs do not need to be
  touched again. Run the playbook at least once in that window. Running it
  for updates is enough.
- **The CA is limited to one domain.** It can only sign names under
  `samba4_manager_ca_permitted_domain`, through an X.509 name constraint. Even
  if its private key leaked, it could not be used to impersonate other sites
  to the PCs that trust it.
- **Use the server name.** Open the app with `samba4_manager_server_name`,
  not by IP address. The certificate is only valid for that name.

### For every PC in the domain, with a GPO

You need a domain-joined Windows PC with the Group Policy Management tools. On
Windows 10/11 Pro or Enterprise, install them from Settings → Optional
features → Add a feature → *RSAT: Group Policy Management Tools*. Log in as a
domain administrator.

1. Copy the CA certificate to that PC. In PowerShell (on Fedora; use the
   Debian path above on Debian/Ubuntu):

   ```
   scp youruser@dc1.example.com:/etc/pki/tls/certs/samba4_manager-ca.crt .
   ```

2. Open **Group Policy Management** (`gpmc.msc`). Under *Forest → Domains*,
   right-click your domain → *Create a GPO in this domain, and Link it here…*.
   Name it, for example, "Trust Samba4 Manager CA".
3. Right-click the new GPO → **Edit**. Go to *Computer Configuration →
   Policies → Windows Settings → Security Settings → Public Key Policies →
   Trusted Root Certification Authorities*. Right-click → **Import…** and
   select `samba4_manager-ca.crt`.
4. PCs apply it at the next reboot, or within about 90 minutes. To apply it
   right away on a PC, run `gpupdate /force`. To check it, open `certlm.msc` →
   *Trusted Root Certification Authorities → Certificates*, and look for
   "Samba4 Manager CA".

Edge and Chrome use the Windows certificate store. If Firefox still warns,
set `security.enterprise_roots.enabled` to `true` in `about:config`, or
through a Firefox enterprise policy.

### On a single PC, by hand

In a Command Prompt run as administrator:

```
certutil -addstore -f Root samba4_manager-ca.crt
```

### Starting over with a new CA

Delete the CA certificate and key on the server (`samba4_manager-ca.crt`
and `samba4_manager-ca.key`), then run the playbook. It creates a new CA and a
new server certificate. Then replace the certificate in the GPO, or on each
PC. If you change `samba4_manager_server_name` to a name outside the CA's
domain, the playbook stops and says so, and leaves the current certificate in
place.

## Troubleshooting

```bash
systemctl status samba4_manager
```

```bash
journalctl -u samba4_manager -e
```

```bash
curl -I http://127.0.0.1:6543/samba4_manager/login
```

(Adjust the path if you changed `samba4_manager_url_path`.) If the last command works but the browser gets a 503 error on Fedora/RHEL,
check that SELinux lets Apache connect:
`getsebool httpd_can_network_connect`.
