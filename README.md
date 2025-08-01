# Two-Tier Architecture: ALB → EC2 → RDS (CloudFormation)

This repository contains the CloudFormation implementation of a two-tier web application architecture.

## Architecture Overview

```
Internet → ALB → EC2 (Auto Scaling Group) → RDS MySQL
```

## Components

- **Application Load Balancer (ALB)**: Distributes traffic across EC2 instances
- **EC2 Instances**: Run the web application in an Auto Scaling Group
- **RDS Database**: MySQL database for persistent data storage
- **VPC & Security Groups**: Network isolation and security

## Prerequisites

- AWS CLI configured
- Python 3.8+
- MySQL client (for database testing)

## Project Structure

```
two-tier-cf-dedicated/
├── README.md
├── requirements.txt
├── template.yaml
├── src/
│   └── app.py
├── tests/
│   └── test_app.py
└── userdata/
    └── install.sh
```

## Deployment

### Using AWS CLI

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Validate CloudFormation template:
   ```bash
   aws cloudformation validate-template --template-body file://template.yaml
   ```

3. Deploy the stack:
   ```bash
   aws cloudformation create-stack \
     --stack-name two-tier-architecture \
     --template-body file://template.yaml \
     --capabilities CAPABILITY_IAM \
     --parameters ParameterKey=DBPassword,ParameterValue=YourSecurePassword123!
   ```

### Using CloudFormation Console

1. Upload the `template.yaml` file to CloudFormation console
2. Create stack with the template
3. Provide required parameters (especially DBPassword)

## Testing

Run the tests:
```bash
pytest tests/
```

## Features

- Auto Scaling based on CPU utilization
- Multi-AZ RDS deployment
- Security groups with minimal required access
- Health checks and monitoring
- User data script for application installation

## Cleanup

```bash
aws cloudformation delete-stack --stack-name two-tier-architecture
```

## API Endpoints

- `GET /` - Home page
- `GET /health` - Health check
- `GET /info` - Application info
- `GET /users` - List users
- `POST /users` - Create user
- `GET /users/{id}` - Get user
- `PUT /users/{id}` - Update user
- `DELETE /users/{id}` - Delete user

## Monitoring

- CloudWatch metrics for ALB and EC2
- RDS performance insights
- Auto Scaling alarms
- Application logs 