output "load_balancer_ip" {
  description = "Point the Cloudflare DNS record here (proxied)"
  value       = hcloud_load_balancer.main.ipv4
}

output "app_server_ips" {
  value = hcloud_server.app[*].ipv4_address
}

output "db_server_ip" {
  value = hcloud_server.db.ipv4_address
}

output "staging_server_ip" {
  value = hcloud_server.staging.ipv4_address
}
