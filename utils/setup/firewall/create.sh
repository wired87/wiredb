gcloud compute firewall-rules create allow-https \
  --allow tcp:443 \
  --target-tags http-server \
  --description "Allow incoming HTTPS traffic" \
  --direction=INGRESS \
  --priority=1000 \
  --network=default \
  --source-ranges=0.0.0.0/0
