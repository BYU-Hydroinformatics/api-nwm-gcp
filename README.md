# api-nwm-gcp
REST API backed by National Water Model data, developed on Google Cloud Platform. This repository contains general architecture diagram for a general understanding, but it focuses on two GCP products and their respective set up files and configurations: Cloud Functions and API Gateway.

--------------------------------
Google Cloud Function (2nd Gen):
Each Cloud Function (CF) corresponds to one GET gate set up through API Gateway. Each CF contains a main.py file and a requirements.txt file, and its basic settings are:

INITIAL SETUP:
- Trigger: HTTPS / Require authentication (Manage authorized users with Cloud IAM)
- Region: us-central1
- Programming language: Python 3.9

RUNTIME:
- Memory allocated: 256 MB
- CPU: 0.167
- Timeout: 60
- Concurrency: 1
- Autoscaling: 0-100
- Runtime service account: function-to-bigquery@nwm-ciroh.iam.gserviceaccount.com

BUILD:
- Default

CONNECTIONS:
- Ingress settings: Allow all traffic
- Egress settings: None

SECURITY AND IMAGE REPO:
- Encryption: Google-managed encryption key
- Image repository: none

--------------------------------
Google API Gateway:
Composed by YAML config file and gateways. It puts all the different Cloud Functions in a single place (API) and it requests end-user to enter a valid API key for validation. API Gateway also receives variables entered by the end-user and takes them to the Cloud Function invoked by the GET request. 

--------------------------------
Service Account:
function-to-bigquery@nwm-ciroh.iam.gserviceaccount.com is set up to access both BigQuery from Cloud Function and Cloud Function from API Gateway. Permissions: BigQuery Job User & Cloud Run Invoked

--------------------------------
Example of currently functional calls (Google Cloud Shell):

->Interacting with Cloud Function:

-- Retroactive Forecast:
Syntax:
curl -m 550 -X GET "https://us-central1-nwm-ciroh.cloudfunctions.net/retroactive_forecast_records?feature_id=[feature_id]&start_date=[start_date]&end_date=[end_date]&reference_time=[reference_time]&ensemble=[ensemble]" \
-H "Authorization: bearer $(gcloud auth print-identity-token)" \
Example:
curl -m 550 -X GET "https://us-central1-nwm-ciroh.cloudfunctions.net/retroactive_forecast_records?feature_id=12068774&start_date=2023-04-04&end_date=2023-04-10&reference_time=2023-03-25T00:00:00&ensemble=0" \
-H "Authorization: bearer $(gcloud auth print-identity-token)" \

-- Geometry Data:
Syntax:
curl -m 550 -X GET "https://us-central1-nwm-ciroh.cloudfunctions.net/geometry?coordinates=[[coord1],[...],[coordN],[coord1]]]" \
-H "Authorization: bearer $(gcloud auth print-identity-token)" \
Example:
curl -m 70 -X GET "https://us-central1-nwm-ciroh.cloudfunctions.net/geometry?coordinates=%5B%5B40.280599,-111.613889%5D,%5B40.219656,-111.614364%5D,%5B40.241428,-111.704668%5D,%5B40.280599,-111.613889%5D%5D" \
-H "Authorization: bearer $(gcloud auth print-identity-token)" \

->Interacting with API Gateway:

curl -H "x-api-key: [Api_key]" "https://retroactive-and-coordinates-9f6idmxh.uc.gateway.dev/geometry?coordinates=%5B%5B40.280599,-111.613889%5D,%5B40.219656,-111.614364%5D,%5B40.241428,-111.704668%5D,%5B40.280599,-111.613889%5D%5D"

curl -H "x-api-key: [Api_key]" "https://api1-9f6idmxh.uc.gateway.dev/retroactive_forecast_records?feature_id=12068774&start_date=2023-04-04&end_date=2023-04-10&reference_time=2023-03-25T00:00:00&ensemble=0"


## Deployment

This section goes over provisioning and deploying the Cloud Functions using terraform. There are a few steps...before beginning make sure you have the [terraform CLI installed](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli) and the [gcloud CLI installed](https://cloud.google.com/sdk/docs/install)


1. Login with [gcloud application default credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc#local-dev) so terraform can run authenticated commands within your cloud environment:

```
gcloud auth application-default login
```

2. Update the variables in `deployment.tfvars` file with the correct information 

3. Initialize terraform config:

```
terraform init
```

4. [Optional] Preview the plan for deployment:

```
terraform plan -var-file="deployment.tfvars"
```

5. Deploy the infrastructure and Cloud Functions 🚀 :

```
terraform apply -var-file="deployment.tfvars"
```

6. [Optional] If you ever need to tear down the cloud infrastructure then you can remove everything and clean-up using the following command:

```
terraform destroy -var-file="deployment.tfvars"
```


## Cloud Run deployment

1. Create Artifact Registry Repo

```
gcloud artifacts repositories create nwm-api-repo --location us-central1 --repository-format docker --async
```

2. Build the Docker Image

```
cd src/ # must be in the src/ subdirectory
gcloud builds submit --config cloudbuild.yaml
```

3. Deploy to Cloud Run

```
gcloud run deploy nwm-api \
--image=<ARTIFACT_REGISTRY_IMAGE> \
--region us-central1 \
--memory=512Mi \
--cpu=1 \
--min-instances=0 \
--max-instances=10 \
--timeout=30s \
--service-account=<SERVICE_ACCOUNT>
```