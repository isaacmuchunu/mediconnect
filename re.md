### Hospital E-Referral System in Django: Comprehensive Design and Features

I'll outline a complete design for a Django-based Hospital E-Referral System. This system facilitates electronic referrals between healthcare providers, allowing primary care doctors to refer patients to specialists or other hospitals securely and efficiently. It includes patient management, doctor directories, referral tracking, notifications, administrative tools, and an ambulance management module for handling emergency transports and patient transfers. The system emphasizes security (e.g., role-based access, data encryption), usability, and scalability.

Since developing the full code here isn't feasible (as it would require thousands of lines), I'll provide:
- A comprehensive list of necessary features, grouped by module.
- A detailed Django project folder structure, with explanations of what each file/directory handles (including key functionalities).
- High-level implementation notes, including models, views, templates, and integrations.

Assumptions:
- Built with Django 5.x (latest as of 2025).
- Uses PostgreSQL for the database (for robustness in handling medical data).
- Frontend: Django templates with Bootstrap for responsive UI; optionally integrate React via Django REST Framework for APIs if scaling to mobile.
- Security: JWT or session-based auth, HTTPS enforcement, audit logging for sensitive actions.
- Compliance: Designed with HIPAA/GDPR in mind (e.g., encrypted patient data, consent tracking), but consult legal experts for production.
- Extras: Celery for background tasks (e.g., notifications), Django Channels for real-time updates.

#### Comprehensive List of Necessary Features

I'll categorize features by core modules. Each module corresponds to a Django app for modularity.

1. **User Authentication and Authorization Module**
   - User registration (patients, doctors, admins, ambulance staff) with email verification.
   - Login/Logout with password reset and two-factor authentication (2FA) option.
   - Role-based access control (RBAC): Patients view their referrals; Doctors manage referrals; Admins oversee everything; Ambulance staff handle dispatches.
   - Profile management: Update personal info, upload photo/ID.
   - Audit logs for all actions (e.g., who viewed patient data or dispatched ambulances).

2. **Patient Management Module**
   - Patient registration with basic demographics (name, age, gender, contact, address).
   - Medical history upload/storage: Allergies, past illnesses, medications (stored securely, e.g., encrypted fields).
   - Consent management: Digital consent forms for data sharing in referrals and ambulance transports.
   - Patient dashboard: View referrals, appointments, ambulance requests, medical summaries.
   - Search and view own referral history with status tracking (e.g., Pending, Accepted, Completed), including linked ambulance dispatches.

3. **Doctor/Provider Management Module**
   - Doctor registration/verification: License number, specialties, hospital affiliation, availability calendar.
   - Directory search: Patients/Doctors search for specialists by name, specialty, location, ratings.
   - Profile: Bio, contact, schedule integration (e.g., Google Calendar API).
   - Dashboard: View incoming referrals, patient queues, performance metrics (e.g., referral acceptance rate), and ambulance coordination for transfers.

4. **Referral Management Module** (Core Feature)
   - Create referral: Doctor selects patient, target specialist/hospital, adds notes, attaches files (e.g., scans, reports), and optionally requests ambulance for transport.
   - Referral workflow: Statuses (Draft, Sent, Viewed, Accepted, Declined, Completed); Automated reminders.
   - Acceptance/Decline: Target doctor reviews and responds with reasons, including ambulance needs.
   - Tracking: Real-time updates via WebSockets; History log for each referral, including ambulance dispatch details.
   - Attachments: Secure file uploads (e.g., PDFs, images) with virus scanning.
   - Integration: Optional API hooks to external EHR systems (e.g., FHIR standards) and ambulance module for seamless transport requests.

5. **Appointment Scheduling Module**
   - Integrated calendar: Book slots based on doctor availability.
   - Automated scheduling: Suggest times during referral acceptance, factoring in ambulance travel time if requested.
   - Reminders: Email/SMS notifications 24 hours before appointments.
   - Cancellation/Rescheduling: With notifications to all parties, including ambulance cancellations.
   - Virtual appointments: Integration with Zoom/Telehealth APIs.

6. **Notification and Communication Module**
   - In-app notifications: Real-time alerts for referral updates, appointments, and ambulance dispatches/arrivals.
   - Email/SMS integration: Using SendGrid/Twilio for confirmations, reminders, and emergency alerts.
   - Messaging: Secure chat between doctors/patients/ambulance staff for referral or transport clarifications.
   - Broadcasts: Admins send system-wide announcements (e.g., policy updates or ambulance availability alerts).

7. **Reporting and Analytics Module**
   - Generate reports: Referral statistics (e.g., by specialty, hospital), patient demographics, wait times, ambulance response times, and utilization rates.
   - Dashboards: Visual charts (using Chart.js or Django's built-in admin).
   - Export: PDF/CSV downloads for audits.
   - Analytics: Track system usage, bottlenecks (e.g., high decline rates or ambulance delays).

8. **Admin and System Management Module**
   - User management: Approve doctor/ambulance staff registrations, ban users.
   - Hospital/Clinic management: Add/edit facilities, assign doctors and ambulances.
   - Backup/Restore: Automated database backups.
   - Settings: Configure email servers, API keys, system themes, and ambulance tracking integrations.
   - Error logging: Integrate with Sentry for monitoring.

9. **Security and Compliance Features**
   - Data encryption: At-rest (database) and in-transit (HTTPS).
   - Access controls: Fine-grained permissions (e.g., doctors can't view unrelated patients; ambulance staff only access dispatch data).
   - Logging: All access to patient data or ambulance logs for audits.
   - CAPTCHA on forms to prevent spam.
   - Rate limiting to prevent DDoS.

10. **Ambulance Management Module**
    - Ambulance fleet management: Register vehicles with details (license plate, type, equipment, capacity).
    - Availability tracking: Real-time status (available, in-use, under maintenance), location via GPS integration (e.g., Google Maps API or third-party tracking).
    - Request ambulance: Direct requests for emergencies or linked to referrals/appointments for patient transfers; include pickup/drop-off locations, urgency level.
    - Dispatch workflow: Assign drivers/staff, route optimization, estimated arrival times; Statuses (Requested, Dispatched, En Route, Arrived, Completed).
    - Real-time tracking: Map views for admins/doctors/patients; WebSockets for live updates.
    - Driver/Staff management: Profiles for ambulance personnel, shift scheduling.
    - Emergency alerts: Automated notifications for critical requests; Integration with hospital alarms.
    - History and logs: Trip records, response times, fuel/maintenance logs for audits.

11. **Additional/Advanced Features**
    - Mobile responsiveness: For access via apps (use Django REST for API endpoints), including mobile ambulance tracking.
    - Multilingual support: Using Django's i18n.
    - Integration with payment gateways (if referrals or ambulance services involve fees).
    - AI enhancements: Suggest specialists or ambulance routes based on patient history/location (using simple ML via scikit-learn).
    - Offline support: Progressive Web App (PWA) features.
    - Testing: Unit/integration tests for all modules.

#### Django Project Folder Structure with Required Functionalities

The project is named `hospital_ereferral`. It uses multiple apps for separation of concerns. Each app handles specific functionalities as described.

```
hospital_ereferral/  # Root project directory
├── manage.py  # Django command-line utility for running servers, migrations, etc.
├── requirements.txt  # List of dependencies (e.g., Django, psycopg2, celery, django-rest-framework, pillow for images, geopy for location handling).
├── .env  # Environment variables (e.g., SECRET_KEY, DATABASE_URL, MAPS_API_KEY) – not committed to Git.
├── static/  # Project-wide static files (CSS, JS, images used globally, e.g., Bootstrap CSS for UI styling, Leaflet.js for maps).
│   ├── css/
│   ├── js/  # Scripts for calendars, notifications, maps (e.g., FullCalendar.js, Google Maps JS API).
│   └── images/  # Logos, icons.
├── media/  # User-uploaded files (e.g., patient scans, doctor licenses, ambulance photos) – stored securely with access controls.
│   ├── referrals/  # Subfolder for referral attachments.
│   ├── profiles/  # User photos.
│   └── ambulances/  # Vehicle documents, photos.
├── templates/  # Project-wide templates (base.html for layout inheritance).
│   └── base.html  # Base template with navbar, footer; includes auth checks for role-based menus.
├── hospital_ereferral/  # Main project package.
│   ├── __init__.py
│   ├── asgi.py  # For ASGI deployment (e.g., with Channels for WebSockets real-time notifications and ambulance tracking).
│   ├── settings.py  # Config: INSTALLED_APPS (list all apps below), DATABASES (PostgreSQL), AUTH_USER_MODEL (custom user), MIDDLEWARE (for security, sessions), TEMPLATES, STATIC/MEDIA roots, CELERY settings.
│   ├── urls.py  # Root URL patterns: Include app URLs, admin site, API endpoints (if using DRF).
│   └── wsgi.py  # For WSGI deployment.
├── users/  # App for authentication and profiles.
│   ├── migrations/  # Database migration files.
│   ├── __init__.py
│   ├── admin.py  # Admin interface for User model (custom filters for roles, including ambulance staff).
│   ├── apps.py
│   ├── models.py  # Custom User model (extends AbstractUser) with roles (Patient/Doctor/Admin/AmbulanceStaff), Profile model for extra fields (e.g., address, specialty, driver license).
│   ├── forms.py  # Forms for registration, login, profile update (with validation for license numbers).
│   ├── views.py  # Views: RegisterView (handle role selection), LoginView, ProfileUpdateView (update info), PasswordResetView.
│   ├── urls.py  # URLs: /register/, /login/, /profile/.
│   ├── templates/users/  # Templates: register.html (form with role dropdown), profile.html (display/edit info).
│   └── tests.py  # Tests: User creation, auth flows.
├── patients/  # App for patient-specific features.
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py  # Admin for PatientHistory model.
│   ├── apps.py
│   ├── models.py  # PatientHistory model (linked to User: allergies, medications – encrypted fields using django-cryptography).
│   ├── views.py  # Views: PatientDashboardView (list referrals/appointments/ambulance requests), HistoryUpdateView (upload medical data).
│   ├── urls.py  # URLs: /patient/dashboard/, /patient/history/.
│   ├── templates/patients/  # dashboard.html (tables for referrals and ambulances), history_form.html.
│   └── tests.py  # Tests: History CRUD.
├── doctors/  # App for doctor management.
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py  # DoctorProfile (specialties, hospital FK), Availability model (calendar slots).
│   ├── views.py  # DoctorSearchView (filter by specialty/location), ProfileView, AvailabilityUpdateView.
│   ├── urls.py  # URLs: /doctors/search/, /doctors/profile/<id>/.
│   ├── templates/doctors/  # search.html (form and results table), profile.html.
│   └── tests.py
├── referrals/  # Core app for referrals.
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py  # Custom admin with workflow actions (e.g., approve referral, link ambulance).
│   ├── apps.py
│   ├── models.py  # Referral model (patient FK, referring_doctor FK, target_doctor FK, status, notes, attachments – FileField with storage in media/, ambulance_request BooleanField).
│   ├── signals.py  # Post-save signals to send notifications or trigger ambulance requests (e.g., via Celery).
│   ├── views.py  # CreateReferralView (form with patient/doctor selection, ambulance checkbox), ReferralDetailView (view/accept/decline), ListReferralsView (filtered by user role).
│   ├── urls.py  # URLs: /referrals/create/, /referrals/<id>/, /referrals/list/.
│   ├── templates/referrals/  # create.html (multi-step form with ambulance option), detail.html (status timeline, attachments viewer, ambulance status).
│   └── tests.py  # Tests: Workflow transitions, including ambulance integration.
├── appointments/  # App for scheduling.
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py  # Appointment model (referral FK, date/time, status, ambulance FK if linked).
│   ├── views.py  # BookAppointmentView (integrated with referral acceptance, factor ambulance ETA), CalendarView (display slots).
│   ├── urls.py  # URLs: /appointments/book/<referral_id>/, /appointments/calendar/.
│   ├── templates/appointments/  # book.html (calendar picker with transport options), list.html.
│   └── tests.py
├── notifications/  # App for alerts and comms.
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py  # Notification model (user FK, message, type – email/in-app/SMS for ambulance alerts).
│   ├── tasks.py  # Celery tasks for sending emails/SMS, including ambulance dispatch confirmations.
│   ├── views.py  # NotificationListView (unread count badge).
│   ├── urls.py  # URLs: /notifications/.
│   ├── templates/notifications/  # list.html (inbox-style).
│   └── tests.py
├── reports/  # App for analytics.
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py  # (Optional) Report model for saved reports.
│   ├── views.py  # ReportGenerateView (query DB, render charts including ambulance metrics), ExportView (PDF/CSV via ReportLab/xlsxwriter).
│   ├── urls.py  # URLs: /reports/generate/, /reports/export/.
│   ├── templates/reports/  # dashboard.html (with embedded charts for referrals and ambulances).
│   └── tests.py
├── ambulances/  # App for ambulance management.
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py  # Admin for Ambulance and Dispatch models (custom filters for status/location).
│   ├── apps.py
│   ├── models.py  # Ambulance model (plate, type, equipment, location – PointField for GIS), Dispatch model (referral/appointment FK, ambulance FK, driver FK, status, route, ETA).
│   ├── views.py  # RequestAmbulanceView (form for location/urgency), DispatchView (assign and track), TrackView (real-time map), FleetListView (availability dashboard).
│   ├── urls.py  # URLs: /ambulances/request/<referral_id>/, /ambulances/track/<dispatch_id>/, /ambulances/fleet/.
│   ├── templates/ambulances/  # request.html (form with map picker), track.html (live map embed), fleet.html (table with statuses).
│   └── tests.py  # Tests: Dispatch workflows, location calculations.
├── admin_panel/  # Custom admin app (extends Django admin).
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py  # Overridden admin site with custom dashboards (including ambulance stats).
│   ├── apps.py
│   ├── views.py  # AdminDashboardView (stats overview, e.g., active ambulances).
│   ├── urls.py  # URLs: /admin/custom/.
│   ├── templates/admin_panel/  # custom_dashboard.html.
│   └── tests.py
└── api/  # (Optional) App for REST APIs (using DRF for mobile integration).
    ├── migrations/
    ├── __init__.py
    ├── serializers.py  # Serializers for models (e.g., ReferralSerializer, AmbulanceSerializer).
    ├── views.py  # APIView sets (e.g., ReferralAPIView, AmbulanceTrackAPIView with auth).
    ├── urls.py  # URLs: /api/referrals/, /api/ambulances/.
    └── tests.py

```

#### Implementation Notes
- **Setup**: Run `django-admin startproject hospital_ereferral`, then `python manage.py startapp <app_name>` for each app. Add apps to `INSTALLED_APPS` in settings.py. For GIS (ambulance locations), add `django.contrib.gis` and use GDAL/GEOS libraries.
- **Database**: Use migrations (`makemigrations`, `migrate`) for models. Seed initial data (e.g., specialties, ambulance types) via fixtures.
- **Frontend**: All templates extend base.html. Use forms from django.forms for validation. Integrate maps with Leaflet or Google Maps for ambulance tracking.
- **Background Tasks**: Celery + Redis for notifications and periodic location updates (e.g., `celery -A hospital_ereferral worker -l info`).
- **Deployment**: Use Docker for containerization, Nginx/Gunicorn for production.
- **Testing**: Aim for 80% coverage with pytest-django.
- **Scalability**: Use caching (Redis) for searches and tracking, sharding if data grows.

This structure is modular and comprehensive. If you need code snippets for specific parts (e.g., a model or view), let me know!