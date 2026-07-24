#!/usr/bin/env bash
set -euo pipefail
: "${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-central1}"
REPOSITORY="${REPOSITORY:-ecommerce}"
CLUSTER="${CLUSTER:-ecommerce}"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/storefront:latest"

gcloud config set project "$PROJECT_ID"
gcloud services enable artifactregistry.googleapis.com cloudbuild.googleapis.com container.googleapis.com

gcloud artifacts repositories describe "$REPOSITORY" --location "$REGION" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "$REPOSITORY" --repository-format=docker --location="$REGION"

gcloud builds submit frontend --config frontend/cloudbuild.yaml \
  --substitutions=_REGION="$REGION",_REPOSITORY="$REPOSITORY",_IMAGE=storefront

gcloud container clusters get-credentials "$CLUSTER" --region "$REGION"
kubectl create namespace ecommerce --dry-run=client -o yaml | kubectl apply -f -
sed -e "s/REGION/$REGION/g" -e "s/PROJECT_ID/$PROJECT_ID/g" k8s/frontend-image-deployment.yaml | kubectl apply -f -
kubectl rollout status deployment/ecommerce-frontend -n ecommerce
kubectl get service ecommerce-frontend -n ecommerce
printf '\nContainer image: %s\n' "$IMAGE"
