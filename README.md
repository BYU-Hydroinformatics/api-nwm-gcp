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


## Infrastructure setup

This section goes over provisioning the cloud resources for the application. These resources include a Service Account, permissions for the service account, and a repository on Artifact Registry to push built Docker images to. There are a few steps...before beginning make sure you have the [terraform CLI installed](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli) and the [gcloud CLI installed](https://cloud.google.com/sdk/docs/install)


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

## Deployment

### Initial Docker build + Cloud Run deploy

After the cloud infrastructure is 

The Docker image build and deploy process are grouped into one Cloud Build process so it

To deploy to Cloud Run from Cloud Build the Cloud Run Admin and Service Account User roles need to be granted to the Cloud Build service account ([source]()). [Open the Cloud Build settings page](https://console.cloud.google.com/cloud-build/settings) and set the status of the Cloud Run Admin role to **ENABLED**.

Next Run 

```
cd src/ # must be in the src/ subdirectory with the main app data
gcloud builds submit --config cloudbuild.yaml
```

There are default 

### Deploy API Gateway

Create the API:

```
gcloud api-gateway apis create API_ID --project=PROJECT_ID
```

Create the API config:

```
gcloud api-gateway api-configs create CONFIG_ID \
  --api=API_ID --openapi-spec=API_DEFINITION \
  --project=PROJECT_ID --backend-auth-service-account=SERVICE_ACCOUNT_EMAIL
```

Deploy an API config to a gateway:

```
gcloud api-gateway gateways create GATEWAY_ID \
  --api=API_ID --api-config=CONFIG_ID \
  --location=GCP_REGION --project=PROJECT_ID
```

### Continuous Deployment



## Example use

See the docs at the following link:

```
export API_KEY=<YOUR-API-KEY>
export NWM_API=<SERVICE-URL>
```

### Geometry



### Analysis Assimilation data

```
curl -H "x-api-key: ${API_KEY}" "${NWM_API}/analysis-assim?start_time=2018-09-17&end_time=2023-05-01&comids=15059811&output_format=csv"
```

### Forecast data

```
curl -H "x-api-key: ${API_KEY}" "${NWM_API}/forecast?forecast_type=long_range&reference_time=2023-05-01&ensemble=0&comids=15059811&output_format=csv"
```