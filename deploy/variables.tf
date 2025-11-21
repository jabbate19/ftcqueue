variable "api_container_image" {
  type        = string
  description = "Docker container to deploy API"
  default     = "jabbate19/ftc-queue-api:latest"
}

variable "gcp_project" {
  type        = string
  description = "GCP Project ID for deployment"
  validation {
    condition     = length(var.gcp_project) > 0
    error_message = "Must provide a valid gcp_project"
  }
}

variable "gcp_region" {
  type        = string
  description = "GCP Region for deployment"
  default     = "us-east4"
}

variable "mysql_user" {
  type        = string
  description = "Username to set for the configured MySQL instance"
  default     = "ftcqueue"
}

variable "mysql_passwd" {
  type        = string
  description = "Password to set for the configured MySQL instance"
  sensitive   = true
  default     = ""
}

variable "mysql_dbname" {
  type        = string
  description = "Name of the DB to create for the configured MySQL instance"
  default     = "ftcqueue"
}

variable "mysql_tier" {
  type        = string
  description = "Instance tier to run the SQL database on, see `gcloud sql tiers list` for options"
  default     = "db-f1-micro"
}

variable "www_domain" {
  type        = string
  description = "Domain to deploy the web app to (must be managed in GCP Cloud DNS)"
  default     = "queue.mycomputerdoesnt.work"
}

variable "request_timeout_seconds" {
  type        = number
  description = "How many seconds before a request is dropped"
  default     = 30

  validation {
    condition     = var.request_timeout_seconds >= 1 && var.request_timeout_seconds <= 60
    error_message = "request_timeout_seconds must be a value between 1 and 60 seconds"
  }
}

variable "discord_token" {
  type        = string
  sensitive   = true
  description = "Discord API token"
}

variable "discord_public_key" {
  type        = string
  sensitive   = true
  description = "Discord Application (Bot) Public key"
}

variable "discord_application_id" {
  type        = number
  sensitive   = true
  description = "Discord Application (Bot) ID"
}

variable "discord_server_id" {
  type        = number
  sensitive   = true
  description = "Discord Server ID"
}


