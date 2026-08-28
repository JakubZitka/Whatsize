resource "hcloud_firewall" "app" {
  name = "whatsize-app"

  rule {
    description = "SSH from admin IPs only"
    direction   = "in"
    protocol    = "tcp"
    port        = "22"
    source_ips  = var.admin_ips
  }

  # API port is reachable only from the private network (the LB targets
  # servers over their private IPs). No public rule for 8000.
  rule {
    description = "API from private network"
    direction   = "in"
    protocol    = "tcp"
    port        = "8000"
    source_ips  = ["10.10.0.0/16"]
  }
}

resource "hcloud_firewall" "db" {
  name = "whatsize-db"

  rule {
    description = "SSH from admin IPs only"
    direction   = "in"
    protocol    = "tcp"
    port        = "22"
    source_ips  = var.admin_ips
  }

  rule {
    description = "Postgres from private subnet only"
    direction   = "in"
    protocol    = "tcp"
    port        = "5432"
    source_ips  = ["10.10.1.0/24"]
  }
}
