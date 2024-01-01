provider "google" {
  project   = var.project_id
  region    = var.region
}

variable services {
  type      = list
  default   = [
    "run.googleapis.com",
  ]
}

resource "google_project_service" "services" {
  for_each  = toset(var.services)
  project   = var.project_id
  service   = each.key
}


resource "google_service_account" "service_account" {
    account_id   = var.sa_name
    display_name = "Cloud Functions Controller"
}

# list of roles to apply to service account
variable "gcp_role_list" {
  description = "The list of roles necceasry for the service account"
  type       = list(string)
  default = [ 
    "roles/bigquery.dataViewer",
    "roles/bigquery.jobUser",
    "roles/run.invoker" 
  ]
}

resource "google_project_iam_binding" "bq_viewer_account_iam" {
    project = var.project_id
    for_each = toset(var.gcp_role_list)
    role    = each.key
    members = [
      "serviceAccount:${google_service_account.service_account.email}",
    ]
}

resource "google_artifact_registry_repository" "nwm-api-repo" {
  location      = "us-central1"
  repository_id = "nwm-api-repo"
  description   = "Repository for the NWM API application"
  format        = "DOCKER"
}

# resource "google_api_gateway_api" "api_gw" {
#   provider = google-beta
#   project = var.project_id
#   api_id = "nwm-api"
# }

# resource "google_api_gateway_api_config" "api_gw" {
#   provider = google-beta
#   project = var.project_id
#   api = google_api_gateway_api.api_gw.api_id
#   api_config_id = "nwm-api-config"

#   openapi_documents {
#     document {
#       path = "spec.yaml"
#       contents = filebase64("../api-gateway/access_points_config.yaml")
#     }
#   }
#   lifecycle {
#     create_before_destroy = true
#   }
# }

# resource "google_api_gateway_gateway" "api_gw" {
#   provider = google-beta
#   project = var.project_id
#   api_config = google_api_gateway_api_config.api_gw.id
#   gateway_id = "nwm-api-gateway"
# }