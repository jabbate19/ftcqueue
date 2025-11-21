terraform {
  required_version = ">= 0.13.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "5.15.0"
    }
    discord = {
      source  = "Lucky3028/discord"
      version = "2.2.1"
    }
  }
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

provider "discord" {
  token = var.discord_token
}