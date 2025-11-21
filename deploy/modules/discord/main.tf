terraform {
  required_version = ">= 0.13.0"

  required_providers {
    discord = {
      source  = "Lucky3028/discord"
      version = "2.2.1"
    }
  }
}

provider "discord" {
  token = var.discord_token
}

data "discord_server" "server" {
  server_id = var.discord_server_id
}

resource "discord_managed_server" "my_server" {
  server_id = data.discord_server.server.id
  name      = "FTC Long Island Queueing"
  region    = "us-east"
}

resource "discord_text_channel" "system" {
  name                     = "discord-notifications"
  server_id                = data.discord_server.server.id
  position                 = 2
  sync_perms_with_category = false
}

resource "discord_system_channel" "system" {
  server_id         = data.discord_server.server.id
  system_channel_id = discord_text_channel.system.id
}

resource "discord_text_channel" "notifications" {
  name                     = "notifications"
  server_id                = data.discord_server.server.id
  position                 = 0
  sync_perms_with_category = false
}

resource "discord_text_channel" "team_roles" {
  name                     = "team-roles"
  server_id                = data.discord_server.server.id
  position                 = 1
  sync_perms_with_category = false
}

resource "discord_message" "how_to_get_roles" {
  channel_id = discord_text_channel.team_roles.id
  content    = "How to Receive Team Roles:\n1. Open a Direct Message with this Bot.\n2. Use the command `/setteam` with your team number to receive your role!\n\nIf needed, `/unssetteam` is available if you need to remove your team role."
}

data "discord_permission" "member" {
  view_channel  = "allow"
  send_messages = "deny"
  read_message_history = "allow"
}

resource "discord_role_everyone" "everyone" {
  server_id   = data.discord_server.server.id
  permissions = data.discord_permission.member.allow_bits
}
