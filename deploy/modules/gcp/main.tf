terraform {
  required_version = ">= 0.13.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "5.15.0"
    }
  }
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

resource "random_password" "defaultmysql" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "random_password" "agent_api_key" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "random_password" "admin_api_key" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}


data "google_project" "project" {
  project_id = var.gcp_project
}

resource "google_project_service" "compute_api" {
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_run_api" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secret_manager" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_sqladmin_api" {
  service            = "sqladmin.googleapis.com"
  disable_on_destroy = false
}

resource "google_sql_database_instance" "tavern-sql-instance" {
  name                = "api-db"
  database_version    = "MYSQL_8_0"
  region              = var.gcp_region
  deletion_protection = false

  settings {
    tier = var.mysql_tier
  }

  depends_on = [
    google_project_service.compute_api,
    google_project_service.cloud_sqladmin_api
  ]
}

resource "google_sql_user" "db-user" {
  instance = google_sql_database_instance.tavern-sql-instance.name
  name     = var.mysql_user
  password = var.mysql_passwd == "" ? random_password.defaultmysql.result : var.mysql_passwd
}

resource "google_sql_database" "api-db" {
  name     = var.mysql_dbname
  instance = google_sql_database_instance.tavern-sql-instance.name
}

resource "google_service_account" "svcwww" {
  account_id  = "svcwww"
  description = "The service account WWW uses to connect to GCP based services. Managed by Terraform."
}

resource "google_project_iam_member" "api-sqlclient-binding" {
  project = var.gcp_project
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.svcwww.email}"
}

resource "google_cloud_run_service" "api" {
  name     = "ftcqueue-api"
  location = var.gcp_region

  traffic {
    percent         = 100
    latest_revision = true
  }

  template {
    spec {
      service_account_name = google_service_account.svcwww.email
      // Controls request timeout, must be long-lived to enable reverse shell support
      timeout_seconds = var.request_timeout_seconds

      containers {
        name  = "api-container"
        image = var.api_container_image

        ports {
          container_port = 8000
        }
        env {
          name  = "DISCORD_TOKEN"
          value = var.discord_token
        }
        env {
          name  = "DISCORD_APPLICATION_ID"
          value = var.discord_application_id
        }
        env {
          name  = "DISCORD_PUBLIC_KEY"
          value = var.discord_public_key
        }
        env {
          name  = "DISCORD_SERVER_ID"
          value = var.discord_server_id
        }
        env {
          name  = "DISCORD_NOTIFICATION_CHANNEL_ID"
          value = var.discord_notifiation_channel_id
        }
        env {
          name  = "DISCORD_API_ENDPOINT"
          value = format("https://%s", var.www_domain)
        }
        env {
          name  = "AGENT_API_KEY"
          value = random_password.agent_api_key.result
        }
        env {
          name  = "ADMIN_API_KEY"
          value = random_password.admin_api_key.result
        }
        env {
          name = "SQL_URI"
          value = format(
            "mysql+pymysql://%s:%s@/%s?unix_socket=/cloudsql/%s",
            google_sql_user.db-user.name,
            google_sql_user.db-user.password,
            google_sql_database.api-db.name,
          google_sql_database_instance.tavern-sql-instance.connection_name)
        }
      }
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"      = 1
        "autoscaling.knative.dev/maxScale"      = 1
        "run.googleapis.com/cloudsql-instances" = google_sql_database_instance.tavern-sql-instance.connection_name
        "run.googleapis.com/client-name"        = "terraform"
        "run.googleapis.com/sessionAffinity"    = true
      }
    }
  }
  autogenerate_revision_name = true

  depends_on = [
    google_project_iam_member.api-sqlclient-binding,
    google_project_service.cloud_run_api,
    google_project_service.cloud_sqladmin_api,
    google_sql_user.db-user,
    google_sql_database.api-db
  ]
}

resource "google_cloud_run_service_iam_binding" "no-auth-required" {
  location = google_cloud_run_service.api.location
  service  = google_cloud_run_service.api.name
  role     = "roles/run.invoker"
  members = [
    "allUsers"
  ]
}

resource "google_cloud_run_domain_mapping" "www-domain" {
  location = google_cloud_run_service.api.location
  name     = var.www_domain

  metadata {
    namespace = google_cloud_run_service.api.project
  }

  spec {
    route_name = google_cloud_run_service.api.name
  }
}
