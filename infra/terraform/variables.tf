variable "hcloud_token" {
  description = "Hetzner Cloud API token (read/write)"
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "Public key installed for the deploy user on all servers"
  type        = string
}

variable "admin_ips" {
  description = "CIDRs allowed to SSH to the servers (your office/VPN IPs)"
  type        = list(string)
}

variable "location" {
  description = "Hetzner location (fsn1 = Falkenstein, nbg1 = Nuremberg)"
  type        = string
  default     = "fsn1"
}

variable "app_server_type" {
  type    = string
  default = "cpx31"
}

variable "db_server_type" {
  type    = string
  default = "cpx41"
}

variable "staging_server_type" {
  type    = string
  default = "cpx21"
}

variable "db_volume_size_gb" {
  type    = number
  default = 100
}

variable "tls_certificate_pem" {
  description = "Cloudflare origin certificate (PEM). Leave empty to serve plain HTTP on the LB until the cert exists."
  type        = string
  default     = ""
  sensitive   = true
}

variable "tls_private_key_pem" {
  description = "Private key for tls_certificate_pem"
  type        = string
  default     = ""
  sensitive   = true
}
