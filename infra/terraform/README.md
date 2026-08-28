# WhatSize infrastructure (Hetzner Cloud)

Provisions the production topology from `docs/deployment-plan.md` §4:
private network, LB11 load balancer, 2× app server, 1× db server with a
100 GB data volume, and a staging server. Region: Falkenstein (fsn1),
EU — GDPR data-residency requirement.

## Apply

```bash
cp terraform.tfvars.example terraform.tfvars   # fill in token, SSH key, admin IPs
terraform init
terraform plan
terraform apply
```

State: for a small team, use a remote backend early — e.g. an S3-compatible
backend on Hetzner Object Storage — so state never lives on one laptop.

## Manual follow-ups after first apply

Deliberately not automated (one-off, and secrets shouldn't pass through
cloud-init):

1. **DB volume encryption (LUKS)** — on `whatsize-db-1`, the attached volume
   appears as `/dev/disk/by-id/scsi-0HC_Volume_*`:
   ```bash
   cryptsetup luksFormat /dev/disk/by-id/scsi-0HC_Volume_<id>
   cryptsetup open /dev/disk/by-id/scsi-0HC_Volume_<id> pgdata
   mkfs.ext4 /dev/mapper/pgdata && mkdir -p /srv/pgdata && mount /dev/mapper/pgdata /srv/pgdata
   ```
   Store the passphrase in the team password manager. The volume must be
   re-opened after a reboot (systemd unit or documented runbook step).
2. **Postgres + pgBackRest** on the db server (data dir on `/srv/pgdata`),
   WAL archiving to Hetzner Object Storage; then schedule the monthly
   restore test.
3. **App servers**: copy `deploy/docker-compose.prod.yml` and a filled-in
   `.env` (from `deploy/.env.example`) to `/srv/whatsize/`.
4. **Cloudflare**: create the proxied DNS record pointing at
   `load_balancer_ip`, issue an origin certificate, and pass it via
   `tls_certificate_pem` / `tls_private_key_pem` (the plain-HTTP LB service
   is replaced by HTTPS automatically on the next apply).
5. **GitHub secrets** for the deploy workflow: `DEPLOY_SSH_KEY` (private key
   of the `deploy` user) and `APP_HOSTS` (the two app server IPs).
6. **Hetzner backups**: enable VM snapshot backups in the console (+20% of
   server price) — intentionally not managed here so a `terraform destroy`
   can never delete them.
