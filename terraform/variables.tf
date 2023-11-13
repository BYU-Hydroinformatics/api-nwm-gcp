variable "project_id" {
    description = "Name of the project to use for the deployment"
    type = string
}

variable "region" {
    description = "Region to deploy the Cloud Functions to"
    type = string
    default = "us-central1"
}

variable "sa_name" {
    description = "Name of the service account to create"
    type = string  
}