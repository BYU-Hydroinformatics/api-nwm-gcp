provider "google" {
  project   = var.project_id
  region    = var.region
}

variable services {
  type      = list
  default   = [
    "cloudfunctions.googleapis.com",
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

resource "google_project_iam_binding" "bq_viewer_account_iam" {
    project = var.project_id
    role    = "roles/bigquery.dataViewer"
    members = [
      "serviceAccount:${var.sa_name}@${var.project_id}.iam.gserviceaccount.com",
    ]
}

resource "google_storage_bucket" "default" {
  name                        = "nwm-api-gcf-staging" # Every bucket name must be globally unique
  location                    = var.region
  uniform_bucket_level_access = true
}

data "archive_file" "default" {
  type        = "zip"
  output_path = "/tmp/forecast-records-source.zip"
  source_dir  = "../src/forecast-records/"
}

resource "google_storage_bucket_object" "forecast_records_source" {
  name   = "forecast-records-source.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.default.output_path # Add path to the zipped function source code
}

resource "google_cloudfunctions2_function" "forecast_records_function" {
  name        = "forecast-records-function"
  location    = var.region
  description = "Function to get forecast records from NWM dataset"

  build_config {
    runtime     = "python39"
    entry_point = "forecast_records" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.forecast_records_source.name
      }
    }
  }

  service_config {
    max_instance_count = 2
    min_instance_count = 0
    available_memory   = "256M"
    timeout_seconds    = 60
    service_account_email = google_service_account.service_account.email
  }
}

# TODO(kmarkert): add other cloud fucntions to terraform