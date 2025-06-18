# Performance Scoring System

A real-time performance evaluation platform built with Flask and AWS, designed for live scoring events with multiple judges, admin oversight, and public viewing.

## Demo
Link to demo: https://drive.google.com/file/d/1LRKD7Omxdnqi7ZC-6Ppx5pOCbW3Pn53o/

## System Architecture

### Tech Stack
- **Frontend**: HTML/CSS, Tailwind CSS, JavaScript
- **Backend**: Python, Flask, Threading
- **Database**: AWS DynamoDB
- **Deployment**: AWS EC2
- **Development Tools**: Git, pip

### Architecture Pattern
- MVC (Model-View-Controller)
- Event-driven architecture
- Polling-based real-time updates

### Dependencies
- boto3 (AWS SDK)
- Flask extensions:
  - flask
  - jsonify
  - make_response
  - render_template_string

### Database Schema

**DynamoDB Tables**:
- `PerformersScores`: Performance scoring data
- `TimerStatus`: System timing and login management
- `judge_credentials`: Authentication information
- `performance_status`: Real-time event status tracking

## Core Features

### User Roles

| Role | Permissions |
|------|-------------|
| Judge | Score entry, View other judges' scores |
| Admin | Monitor event status, View all scores |
| Public | View live events, scores, final results |

### Real-time Event Management
- Synchronized login system
- Automated performance timing
- Score submission windows
- Live status updates

## Workflow

### 1. System Initialization
```python
# Database connection setup
dynamodb = boto3.resource(
    'dynamodb',
    region_name='us-west-1',
    aws_access_key_id='your_access_key',
    aws_secret_access_key='your_secret_key'
)
```

### Key Components

**1. Performance Timer System**
- 10-second performance windows
- 30-second judge scoring windows
- Automated state transitions

**2. Status Management**
```python
def update_performance_status(performer_id, event_status):
    performance_status.update_item(
        Key={'performer_id': f'performer_{performer_id}'},
        UpdateExpression="SET event_status = :status",
        ExpressionAttributeValues={':status': event_status}
    )
```

**3. Score Management**
- Real-time score entry
- Score validation
- Total score calculation

## Event Workflow

1. **System Initialization**
   - Database connections established
   - Tables verified
   - Global state initialized

2. **Login Phase**
   - System monitors login count
   - Requires exactly 3 users
   - Role verification

3. **Performance Cycle**
   - Performance timer (10 seconds)
   - Score entry window (30 seconds)
   - Status updates
   - Score recording

4. **Event Completion**
   - Final score calculation
   - Status updates
   - System reset capability

## Installation & Deployment

### Prerequisites
- Python 3.x
- AWS Account
- EC2 Instance
- Required Python packages

### Setup Steps

1. **Clone Repository**
```bash
git clone https://github.com/sohan2000/online-scoring-system
cd online-scoring-system
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure AWS**
```bash
aws configure
# Enter your AWS credentials
```

4. **Environment Variables**
```bash
export AWS_REGION="us-west-1"
export FLASK_APP="app.py"
export FLASK_ENV="production"
```

5. **Database Setup**
- Create required DynamoDB tables
- Configure table schemas
- Set up IAM roles

### EC2 Deployment

1. **Instance Setup**
   - Launch EC2 instance
   - Configure security groups
   - Install dependencies

2. **Application Deployment**
   - Transfer application files
   - Configure environment
   - Start application server

## Security Considerations

- AWS IAM role configuration
- Secure credential management
- Session handling
- Access control implementation

## Error Handling

The system implements comprehensive error handling for:
- Database operations
- Login synchronization
- Score submission
- Timer management

## Monitoring (Future Scope)

- AWS CloudWatch integration
- Error logging
- Performance metrics
- Real-time monitoring

## Support

For technical support or queries:
- Email: sohan.vallapureddy@sjsu.edu, jyothi.vaidyanathan@sjsu.edu

```

This README provides a comprehensive overview of the performance scoring system, detailing its architecture, features, implementation, and deployment process. The system is designed for real-time event management with multiple user roles and synchronized timing controls, leveraging AWS services for reliability and scalability.
