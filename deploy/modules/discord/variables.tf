variable "discord_token" {
  type        = string
  sensitive   = true
  description = "Discord API token"
}

variable "discord_server_id" {
  type        = number
  sensitive   = true
  description = "Discord Server ID"
}