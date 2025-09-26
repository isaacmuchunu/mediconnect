# MediConnect API Documentation

## Overview

MediConnect is a comprehensive hospital e-referral and emergency medical coordination system providing RESTful APIs for healthcare providers, ambulance services, and emergency responders.

**Base URL**: `https://api.mediconnect.com/`  
**API Version**: v1  
**Authentication**: Token-based authentication required for all endpoints

---

## Authentication

### Token Authentication
All API requests must include an authentication token in the header:

```http
Authorization: Token YOUR_API_TOKEN
```

### Obtain Token
```http
POST /api/auth/token/
Content-Type: application/json

{
    "username": "your_username",
    "password": "your_password"
}
```

**Response:**
```json
{
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
    "user_id": 123,
    "role": "DISPATCHER"
}
```

---

## Core API Endpoints

### 1. Emergency Call Management

#### Create Emergency Call
```http
POST /api/emergency/calls/
Content-Type: application/json

{
    "caller_phone": "+1-555-0123",
    "caller_name": "John Doe",
    "incident_address": "123 Main St, NYC",
    "patient_name": "Jane Smith",
    "patient_age": 45,
    "patient_gender": "F",
    "chief_complaint": "Chest pain",
    "priority": "critical",
    "call_type": "medical"
}
```

#### List Emergency Calls
```http
GET /api/emergency/calls/
```

**Query Parameters:**
- `status`: Filter by call status (received, processing, dispatched, completed)
- `priority`: Filter by priority (routine, urgent, emergency, critical)
- `search`: Search by call number, patient name, or caller name

#### Get Call Details
```http
GET /api/emergency/calls/{call_id}/
```

#### Quick Dispatch
```http
POST /api/emergency/quick-dispatch/
Content-Type: application/json

{
    "call_id": "uuid",
    "ambulance_id": "uuid"
}
```

### 2. Ambulance Management

#### List Ambulances
```http
GET /api/ambulances/
```

**Query Parameters:**
- `status`: available, dispatched, en_route, on_scene, out_of_service
- `location`: Coordinates for proximity search
- `type`: Ambulance type filter

#### Update Ambulance Status
```http
POST /api/ambulances/status/
Content-Type: application/json

{
    "ambulance_id": "uuid",
    "status": "en_route",
    "notes": "Responding to emergency call"
}
```

#### Update GPS Location
```http
POST /api/ambulances/gps/
Content-Type: application/json

{
    "ambulance_id": "uuid",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "accuracy": 10.0,
    "speed": 35.5,
    "heading": 180.0
}
```

#### Real-time Location Stream
```http
GET /api/ambulances/location-stream/{ambulance_id}/
```

### 3. Hospital Integration

#### Hospital Status
```http
GET /api/hospitals/{hospital_id}/status/
```

**Response:**
```json
{
    "hospital_id": "uuid",
    "name": "General Hospital",
    "emergency_department": {
        "status": "open",
        "wait_time_minutes": 45,
        "capacity_percentage": 85,
        "diversion_status": false
    },
    "bed_availability": {
        "total_beds": 200,
        "available_beds": 15,
        "icu_beds": 5,
        "emergency_beds": 8
    },
    "last_updated": "2024-01-15T10:30:00Z"
}
```

#### Update Hospital Status
```http
POST /api/hospitals/{hospital_id}/status/
Content-Type: application/json

{
    "emergency_department": {
        "status": "diversion",
        "wait_time_minutes": 120,
        "reason": "Overcapacity"
    },
    "bed_availability": {
        "available_beds": 5,
        "icu_beds": 1
    }
}
```

#### Hospital Recommendations
```http
POST /api/hospitals/recommend/
Content-Type: application/json

{
    "patient_condition": "cardiac arrest",
    "ambulance_location": {
        "latitude": 40.7128,
        "longitude": -74.0060
    },
    "specialty_required": "cardiology",
    "priority": "critical"
}
```

### 4. Dispatch Management

#### Create Dispatch
```http
POST /api/dispatches/
Content-Type: application/json

{
    "referral_id": "uuid",
    "ambulance_id": "uuid",
    "priority": "emergency",
    "pickup_address": "123 Main St",
    "destination_address": "456 Hospital Ave",
    "special_instructions": "Patient has chest pain"
}
```

#### Update Dispatch Status
```http
PUT /api/dispatches/{dispatch_id}/status/
Content-Type: application/json

{
    "status": "on_scene",
    "notes": "Arrived at scene, patient assessment in progress"
}
```

#### List Active Dispatches
```http
GET /api/dispatches/active/
```

### 5. Notification System

#### Send Notification
```http
POST /api/notifications/send/
Content-Type: application/json

{
    "recipients": ["user1", "user2"],
    "message": {
        "title": "Emergency Alert",
        "body": "Mass casualty incident reported",
        "priority": "emergency",
        "data": {
            "incident_type": "mass_casualty",
            "location": "Downtown area"
        }
    },
    "channels": ["sms", "push", "email"]
}
```

#### Emergency Alert Broadcast
```http
POST /api/notifications/emergency-alert/
Content-Type: application/json

{
    "alert_type": "MASS_CASUALTY",
    "message": "Multiple vehicle accident on I-95",
    "affected_areas": ["Zone_A", "Zone_B"],
    "priority": "emergency"
}
```

#### User Notification Preferences
```http
GET /api/notifications/preferences/
PUT /api/notifications/preferences/
```

### 6. Referral Management

#### Create Referral
```http
POST /api/referrals/
Content-Type: application/json

{
    "patient_id": "uuid",
    "referring_doctor": "uuid",
    "receiving_hospital": "uuid",
    "specialty": "cardiology",
    "urgency_level": "urgent",
    "medical_history": "Previous MI",
    "current_symptoms": "Chest pain, SOB",
    "insurance_info": "Medicare #123456789"
}
```

#### Update Referral Status
```http
PUT /api/referrals/{referral_id}/
Content-Type: application/json

{
    "status": "accepted",
    "receiving_doctor": "uuid",
    "scheduled_datetime": "2024-01-16T14:30:00Z",
    "notes": "Scheduled for emergency catheterization"
}
```

---

## Real-time WebSocket APIs

### Ambulance Tracking
```javascript
// Connect to ambulance tracking
const socket = new WebSocket('ws://api.mediconnect.com/ws/ambulance/{ambulance_id}/');

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    // Handle real-time location updates
};
```

### Emergency Alerts
```javascript
// Connect to emergency alerts
const socket = new WebSocket('ws://api.mediconnect.com/ws/emergency-alerts/');

socket.onmessage = function(event) {
    const alert = JSON.parse(event.data);
    // Handle emergency alerts
};
```

### Dispatch Center
```javascript
// Connect to dispatch center updates
const socket = new WebSocket('ws://api.mediconnect.com/ws/dispatch/');

socket.onmessage = function(event) {
    const update = JSON.parse(event.data);
    // Handle dispatch updates
};
```

---

## Response Codes

| Code | Description |
|------|-------------|
| 200  | Success |
| 201  | Created |
| 400  | Bad Request |
| 401  | Unauthorized |
| 403  | Forbidden |
| 404  | Not Found |
| 429  | Rate Limit Exceeded |
| 500  | Internal Server Error |
| 503  | Service Unavailable |

---

## Rate Limiting

- **Anonymous users**: 100 requests per hour
- **Authenticated users**: 1000 requests per hour
- **Emergency endpoints**: 5000 requests per hour
- **Real-time GPS updates**: No limit

---

## Error Response Format

```json
{
    "error": {
        "code": "INVALID_REQUEST",
        "message": "The request is missing required parameters",
        "details": {
            "missing_fields": ["patient_id", "priority"]
        },
        "timestamp": "2024-01-15T10:30:00Z"
    }
}
```

---

## Data Models

### Emergency Call
```json
{
    "id": "uuid",
    "call_number": "CALL-20240115-001",
    "caller_phone": "+1-555-0123",
    "caller_name": "John Doe",
    "incident_address": "123 Main St, NYC",
    "patient_name": "Jane Smith",
    "patient_age": 45,
    "chief_complaint": "Chest pain",
    "priority": "critical",
    "status": "dispatched",
    "received_at": "2024-01-15T10:30:00Z",
    "dispatched_at": "2024-01-15T10:33:00Z"
}
```

### Ambulance
```json
{
    "id": "uuid",
    "license_plate": "AMB-001",
    "call_sign": "Unit 12",
    "status": "available",
    "current_location": {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy": 10.0
    },
    "ambulance_type": "ALS",
    "crew": [
        {
            "name": "John Smith",
            "role": "paramedic",
            "certification": "NREMT-P"
        }
    ]
}
```

---

## SDK Examples

### Python SDK
```python
import mediconnect

client = mediconnect.Client(api_token='your_token')

# Create emergency call
call = client.emergency_calls.create({
    'caller_phone': '+1-555-0123',
    'patient_name': 'Jane Doe',
    'chief_complaint': 'Chest pain',
    'priority': 'critical'
})

# Update ambulance location
client.ambulances.update_location(
    ambulance_id='uuid',
    latitude=40.7128,
    longitude=-74.0060
)
```

### JavaScript SDK
```javascript
import MediConnect from 'mediconnect-js';

const client = new MediConnect({
    apiToken: 'your_token',
    baseURL: 'https://api.mediconnect.com'
});

// Send emergency alert
await client.notifications.sendEmergencyAlert({
    alertType: 'MASS_CASUALTY',
    message: 'Multiple vehicle accident',
    affectedAreas: ['Zone_A']
});
```

---

## Webhook Integration

### Emergency Call Events
```http
POST https://your-server.com/webhooks/emergency-calls
Content-Type: application/json

{
    "event": "call.created",
    "data": {
        "call_id": "uuid",
        "priority": "critical",
        "location": "123 Main St"
    },
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### Ambulance Status Events
```http
POST https://your-server.com/webhooks/ambulance-status
Content-Type: application/json

{
    "event": "ambulance.status_changed",
    "data": {
        "ambulance_id": "uuid",
        "old_status": "available",
        "new_status": "dispatched"
    },
    "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Security Considerations

1. **HIPAA Compliance**: All patient data is encrypted and access is logged
2. **Authentication**: Token-based authentication with expiration
3. **Rate Limiting**: Prevents API abuse and ensures fair usage
4. **Data Validation**: All inputs are validated and sanitized
5. **Audit Logging**: All API calls are logged for compliance
6. **HTTPS Only**: All communication must use HTTPS
7. **IP Whitelisting**: Optional IP restriction for sensitive endpoints

---

## Support

- **Documentation**: https://docs.mediconnect.com
- **API Status**: https://status.mediconnect.com
- **Support Email**: api-support@mediconnect.com
- **Emergency Contact**: +1-800-MEDIC-01

---

*Last Updated: January 15, 2024*
*API Version: 1.0*