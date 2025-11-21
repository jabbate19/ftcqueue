module "discord" {
    source = "./modules/discord"
    
    discord_server_id = var.discord_server_id
    discord_token     = var.discord_token
}

module "gcp" {
    source = "./modules/gcp"
    
    gcp_project               = var.gcp_project
    gcp_region                = var.gcp_region
    api_container_image       = var.api_container_image
    discord_token             = var.discord_token
    discord_application_id    = var.discord_application_id
    discord_public_key        = var.discord_public_key
    discord_server_id         = var.discord_server_id
    www_domain                = var.www_domain
    discord_notifiation_channel_id = module.discord.notification_channel_id
}