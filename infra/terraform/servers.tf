resource "hcloud_ssh_key" "deploy" {
  name       = "whatsize-deploy"
  public_key = var.ssh_public_key
}

locals {
  app_cloud_init = templatefile("${path.module}/cloud-init/server.yaml.tftpl", {
    ssh_public_key = var.ssh_public_key
  })
}

resource "hcloud_server" "app" {
  count       = 2
  name        = "whatsize-app-${count.index + 1}"
  server_type = var.app_server_type
  image       = "debian-12"
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.deploy.id]
  user_data   = local.app_cloud_init

  firewall_ids = [hcloud_firewall.app.id]

  network {
    network_id = hcloud_network.main.id
    ip         = "10.10.1.1${count.index + 1}" # 10.10.1.11, 10.10.1.12
  }

  depends_on = [hcloud_network_subnet.main]
}

resource "hcloud_server" "db" {
  name        = "whatsize-db-1"
  server_type = var.db_server_type
  image       = "debian-12"
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.deploy.id]
  user_data   = local.app_cloud_init

  firewall_ids = [hcloud_firewall.db.id]

  network {
    network_id = hcloud_network.main.id
    ip         = "10.10.1.20"
  }

  depends_on = [hcloud_network_subnet.main]
}

# Data volume for Postgres. LUKS encryption + filesystem are set up once by
# hand after first apply — see README.md in this directory.
resource "hcloud_volume" "db_data" {
  name     = "whatsize-db-data"
  size     = var.db_volume_size_gb
  location = var.location
}

resource "hcloud_volume_attachment" "db_data" {
  volume_id = hcloud_volume.db_data.id
  server_id = hcloud_server.db.id
  automount = false # mounted via LUKS mapping, not raw
}

resource "hcloud_server" "staging" {
  name        = "whatsize-staging"
  server_type = var.staging_server_type
  image       = "debian-12"
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.deploy.id]
  user_data   = local.app_cloud_init

  firewall_ids = [hcloud_firewall.app.id]

  network {
    network_id = hcloud_network.main.id
    ip         = "10.10.1.30"
  }

  depends_on = [hcloud_network_subnet.main]
}
