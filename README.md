# k8s-sqs-autoscaler
Kubernetes pod autoscaler based on queue size in AWS SQS

## Usage
Create a kubernetes deployment like this:
```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redaction-sqs-auto-scaler
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redaction-sqs-auto-scaler
  template:
    metadata:
      labels:
        app: redaction-sqs-auto-scaler
    spec:
      serviceAccountName: data-service-account
      containers:
      - name: redaction-sqs-auto-scaler
        image: 691195436300.dkr.ecr.us-east-1.amazonaws.com/k8s-sqs-autoscaler:latest
        command:
            - ./k8s-sqs-autoscaler
            - --sqs-queue-url=https://sqs.us-east-1.amazonaws.com/691195436300/casemaker_redaction_dev
            - --kubernetes-deployment=redaction_service
            - --kubernetes-deployment-file=../services/redaction_service.yaml
            - --kubernetes-namespace=default
            - --aws-region=us-east-1
            - --poll-period=10 # optional
            - --scale-down-cool-down=300000000000 # optional
            - --scale-up-cool-down=10 # optional
            - --scale-up-messages=1 # optional
            - --scale-down-messages=0 # optional
            - --max-pods=30 # optional
            - --min-pods=0 # optional
        env:
            -
                name: AWS_DEFAULT_REGION
                value: us-east-1
            # - name: geo
            #   valueFrom:
            #     fieldRef:
            #       fieldPath: metadata.namespace
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        ports:
        - containerPort: 80
      # nodeSelector:
      #   nodeType: master

```
