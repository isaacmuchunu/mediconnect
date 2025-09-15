# 🔌 MediConnect API Documentation

## 📋 **API OVERVIEW**

MediConnect provides a comprehensive RESTful API for all system operations, enabling seamless integration with external systems, mobile applications, and third-party services.

### **Base URL**
```
Production: https://your-domain.com/api/
Development: http://127.0.0.1:8000/api/
```

### **Authentication**
All API endpoints require authentication using Django's built-in authentication system or API tokens.

```http
Authorization: Token your_api_token_here
Content-Type: application/json
```

---

## 🚨 **EMERGENCY CALL MANAGEMENT API**

### **Create Emergency Call**
```http
POST /api/emergency/calls/
```

**Request Body:**
```json
{
    "caller_name": "John Doe",
    "caller_phone": "+1234567890",
    "incident_location": "123 Main St, City, State",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "emergency_type": "medical",
    "priority_level": "high",
    "description": "Chest pain, difficulty breathing",
    "patient_age": 65,
    "patient_gender": "male",
    "conscious": true,
    "breathing": true
}
```

**Response:**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "call_number": "EC-2024-001234",
    "status": "active",
    "priority_score": 85,
    "created_at": "2024-01-15T10:30:00Z",
    "estimated_response_time": 8
}
```

### **Quick Dispatch**
```http
POST /api/emergency/quick-dispatch/
```

**Request Body:**
```json
{
    "emergency_call_id": "550e8400-e29b-41d4-a716-446655440000",
    "ambulance_id": "660e8400-e29b-41d4-a716-446655440001",
    "priority": "urgent"
}
```

### **Update Call Status**
```http
PATCH /api/emergency/calls/{call_id}/status/
```

**Request Body:**
```json
{
    "status": "dispatched",
    "notes": "Ambulance en route"
}
```

---

## 📍 **GPS TRACKING API**

### **Update GPS Location (Enhanced)**
```http
POST /api/gps/update-enhanced/
```

**Request Body:**
```json
{
    "ambulance_id": "660e8400-e29b-41d4-a716-446655440001",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "altitude": 10.5,
    "accuracy": 5.0,
    "speed_kmh": 45.0,
    "heading_degrees": 180,
    "emergency_lights": true,
    "siren_active": true,
    "battery_level": 85,
    "data_source": "mobile_app"
}
```

**Response:**
```json
{
    "status": "success",
    "timestamp": "2024-01-15T10:35:00Z",
    "location_id": "770e8400-e29b-41d4-a716-446655440002"
}
```

### **Route Optimization**
```http
POST /api/gps/optimize-route/
```

**Request Body:**
```json
{
    "ambulance_id": "660e8400-e29b-41d4-a716-446655440001",
    "origin": {
        "latitude": 40.7128,
        "longitude": -74.0060
    },
    "destination": {
        "latitude": 40.7589,
        "longitude": -73.9851
    },
    "emergency_priority": "high",
    "avoid_traffic": true
}
```

**Response:**
```json
{
    "route_id": "880e8400-e29b-41d4-a716-446655440003",
    "estimated_duration_minutes": 12,
    "distance_km": 8.5,
    "route_points": [
        {"lat": 40.7128, "lng": -74.0060},
        {"lat": 40.7200, "lng": -74.0000},
        {"lat": 40.7589, "lng": -73.9851}
    ],
    "traffic_conditions": "moderate",
    "alternative_routes": 2
}
```

### **Location Stream (WebSocket)**
```
ws://your-domain.com/ws/gps/location-stream/{ambulance_id}/
```

**Real-time Location Updates:**
```json
{
    "type": "location_update",
    "ambulance_id": "660e8400-e29b-41d4-a716-446655440001",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "speed_kmh": 45.0,
    "heading": 180,
    "timestamp": "2024-01-15T10:35:00Z"
}
```

---

## 🏥 **HOSPITAL INTEGRATION API**

### **Hospital Availability**
```http
GET /api/hospitals/availability/
```

**Query Parameters:**
- `emergency_type`: Type of emergency (optional)
- `specialty`: Required specialty (optional)
- `lat`: Latitude for distance calculation
- `lng`: Longitude for distance calculation

**Response:**
```json
{
    "status": "success",
    "hospitals": [
        {
            "id": "990e8400-e29b-41d4-a716-446655440004",
            "name": "City General Hospital",
            "address": "456 Hospital Ave, City, State",
            "distance_km": 3.2,
            "capacity": {
                "status": "normal",
                "available_beds": 25,
                "occupancy_rate": 75,
                "icu_beds_available": 5,
                "can_accept_patients": true
            },
            "ed_status": {
                "is_open": true,
                "average_wait_time": 15,
                "trauma_center": true,
                "can_accept_ambulances": true
            },
            "specialty_units": [
                {
                    "type": "icu",
                    "name": "Intensive Care Unit",
                    "available_capacity": 5,
                    "wait_time_minutes": 0,
                    "can_accept_patients": true
                }
            ]
        }
    ],
    "total_available": 1
}
```

### **Update Hospital Capacity**
```http
POST /api/hospitals/capacity/update/
```

**Request Body:**
```json
{
    "hospital_id": "990e8400-e29b-41d4-a716-446655440004",
    "total_beds": 100,
    "occupied_beds": 75,
    "reserved_beds": 5,
    "ed_wait_time_minutes": 15,
    "ed_patients_waiting": 8,
    "icu_beds_available": 5,
    "ambulance_diversion": false
}
```

### **Update ED Status**
```http
POST /api/hospitals/ed/update/
```

**Request Body:**
```json
{
    "hospital_id": "990e8400-e29b-41d4-a716-446655440004",
    "is_open": true,
    "diversion_status": false,
    "level_1_wait_minutes": 0,
    "level_2_wait_minutes": 5,
    "level_3_wait_minutes": 15,
    "level_4_wait_minutes": 30,
    "level_5_wait_minutes": 60,
    "patients_waiting": 8,
    "physicians_on_duty": 4,
    "nurses_on_duty": 12
}
```

---

## 📱 **MOBILE API ENDPOINTS**

### **Mobile GPS Update**
```http
POST /api/mobile/gps/
```

**Request Body:**
```json
{
    "latitude": 40.7128,
    "longitude": -74.0060,
    "accuracy": 5.0,
    "speed_kmh": 45.0,
    "heading_degrees": 180,
    "emergency_lights": true,
    "siren_active": true,
    "battery_level": 85
}
```

### **Quick Status Update**
```http
POST /api/mobile/status/
```

**Request Body:**
```json
{
    "status": "en_route"
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Status updated to en_route",
    "new_status": "en_route"
}
```

---

## 💬 **COMMUNICATIONS API**

### **Send Notification**
```http
POST /api/communications/notifications/send/
```

**Request Body:**
```json
{
    "recipient_user_id": "aa0e8400-e29b-41d4-a716-446655440005",
    "subject": "Emergency Dispatch Alert",
    "message": "New emergency call assigned to your ambulance",
    "notification_type": "emergency_dispatch",
    "priority": "urgent",
    "channels": ["push", "sms"]
}
```

### **Create Secure Message**
```http
POST /api/communications/messages/
```

**Request Body:**
```json
{
    "recipients": ["bb0e8400-e29b-41d4-a716-446655440006"],
    "subject": "Patient Handoff Information",
    "message": "Patient details for incoming ambulance...",
    "message_type": "handoff",
    "related_patient": "patient_id_123"
}
```

### **Emergency Alert**
```http
POST /api/communications/alerts/
```

**Request Body:**
```json
{
    "title": "Mass Casualty Incident",
    "message": "Multiple vehicle accident on Highway 101",
    "alert_type": "mass_casualty",
    "severity": "critical",
    "target_roles": ["PARAMEDIC", "EMT", "DISPATCHER"],
    "requires_acknowledgment": true
}
```

---

## 📊 **ANALYTICS API**

### **Widget Data**
```http
GET /api/analytics/widget/{widget_id}/data/
```

**Query Parameters:**
- `range`: Time range (1h, 24h, 7d, 30d)

**Response:**
```json
{
    "status": "success",
    "data": {
        "labels": ["00:00", "01:00", "02:00", "03:00"],
        "datasets": [{
            "label": "Dispatch Volume",
            "data": [5, 3, 2, 4],
            "backgroundColor": "#3b82f6"
        }]
    },
    "last_updated": "2024-01-15T10:35:00Z"
}
```

### **Log Analytics Event**
```http
POST /api/analytics/events/log/
```

**Request Body:**
```json
{
    "event_type": "dispatch_created",
    "event_name": "Emergency Dispatch Created",
    "event_data": {
        "emergency_type": "medical",
        "priority": "high",
        "response_time": 8
    },
    "duration_ms": 1500
}
```

---

## 🔐 **AUTHENTICATION & SECURITY**

### **Obtain API Token**
```http
POST /api/auth/token/
```

**Request Body:**
```json
{
    "username": "your_username",
    "password": "your_password"
}
```

**Response:**
```json
{
    "token": "your_api_token_here",
    "user_id": "cc0e8400-e29b-41d4-a716-446655440007",
    "expires_at": "2024-01-16T10:30:00Z"
}
```

### **Refresh Token**
```http
POST /api/auth/token/refresh/
```

### **User Profile**
```http
GET /api/auth/user/
```

**Response:**
```json
{
    "id": "cc0e8400-e29b-41d4-a716-446655440007",
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "PARAMEDIC",
    "is_active": true,
    "last_login": "2024-01-15T09:00:00Z"
}
```

---

## 📝 **ERROR HANDLING**

### **Standard Error Response**
```json
{
    "status": "error",
    "message": "Detailed error message",
    "code": "ERROR_CODE",
    "details": {
        "field": ["Field-specific error message"]
    }
}
```

### **HTTP Status Codes**
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `429`: Rate Limited
- `500`: Internal Server Error

---

## 🚀 **RATE LIMITING**

API endpoints are rate-limited to ensure system stability:

- **Authentication**: 5 requests per minute
- **GPS Updates**: 120 requests per minute
- **General API**: 60 requests per minute
- **Analytics**: 30 requests per minute

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642248600
```

---

## 🔄 **WEBHOOKS**

### **Webhook Events**
MediConnect can send webhooks for various events:

- `emergency_call.created`
- `dispatch.assigned`
- `ambulance.status_changed`
- `hospital.capacity_updated`
- `alert.created`

### **Webhook Payload Example**
```json
{
    "event": "dispatch.assigned",
    "timestamp": "2024-01-15T10:30:00Z",
    "data": {
        "dispatch_id": "dd0e8400-e29b-41d4-a716-446655440008",
        "ambulance_id": "660e8400-e29b-41d4-a716-446655440001",
        "emergency_call_id": "550e8400-e29b-41d4-a716-446655440000",
        "priority": "urgent"
    }
}
```

---

## 📚 **SDK & LIBRARIES**

### **JavaScript SDK**
```javascript
import MediConnectAPI from 'mediconnect-js-sdk';

const api = new MediConnectAPI({
    baseURL: 'https://your-domain.com/api/',
    token: 'your_api_token'
});

// Create emergency call
const call = await api.emergency.createCall({
    caller_name: 'John Doe',
    incident_location: '123 Main St',
    emergency_type: 'medical'
});
```

### **Python SDK**
```python
from mediconnect import MediConnectAPI

api = MediConnectAPI(
    base_url='https://your-domain.com/api/',
    token='your_api_token'
)

# Update GPS location
api.gps.update_location(
    ambulance_id='660e8400-e29b-41d4-a716-446655440001',
    latitude=40.7128,
    longitude=-74.0060
)
```

---

## 🧪 **TESTING**

### **API Testing with cURL**
```bash
# Test emergency call creation
curl -X POST https://your-domain.com/api/emergency/calls/ \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "caller_name": "Test User",
    "incident_location": "Test Location",
    "emergency_type": "medical"
  }'
```

### **Postman Collection**
Import our Postman collection for comprehensive API testing:
`https://your-domain.com/api/postman-collection.json`

---

**📞 For API support, contact our development team or check the interactive API documentation at `/api/docs/`**
