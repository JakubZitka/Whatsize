resource "hcloud_load_balancer" "main" {
  name               = "whatsize-lb"
  load_balancer_type = "lb11"
  location           = var.location
}

resource "hcloud_load_balancer_network" "main" {
  load_balancer_id = hcloud_load_balancer.main.id
  network_id       = hcloud_network.main.id
  ip               = "10.10.1.5"
}

resource "hcloud_load_balancer_target" "app" {
  count            = length(hcloud_server.app)
  type             = "server"
  load_balancer_id = hcloud_load_balancer.main.id
  server_id        = hcloud_server.app[count.index].id
  use_private_ip   = true

  depends_on = [hcloud_load_balancer_network.main]
}

# Cloudflare origin certificate, uploaded when provided. Until then the LB
# serves plain HTTP (fine for smoke tests, not for production traffic).
resource "hcloud_uploaded_certificate" "origin" {
  count       = var.tls_certificate_pem != "" ? 1 : 0
  name        = "whatsize-cloudflare-origin"
  certificate = var.tls_certificate_pem
  private_key = var.tls_private_key_pem
}

resource "hcloud_load_balancer_service" "https" {
  count            = var.tls_certificate_pem != "" ? 1 : 0
  load_balancer_id = hcloud_load_balancer.main.id
  protocol         = "https"
  listen_port      = 443
  destination_port = 8000

  http {
    certificates = [hcloud_uploaded_certificate.origin[0].id]
  }

  health_check {
    protocol = "http"
    port     = 8000
    interval = 10
    timeout  = 5
    retries  = 3
    http {
      path         = "/healthz"
      status_codes = ["200"]
    }
  }
}

resource "hcloud_load_balancer_service" "http" {
  # Kept only while no certificate is configured; remove once HTTPS is live.
  count            = var.tls_certificate_pem != "" ? 0 : 1
  load_balancer_id = hcloud_load_balancer.main.id
  protocol         = "http"
  listen_port      = 80
  destination_port = 8000

  health_check {
    protocol = "http"
    port     = 8000
    interval = 10
    timeout  = 5
    retries  = 3
    http {
      path         = "/healthz"
      status_codes = ["200"]
    }
  }
}
