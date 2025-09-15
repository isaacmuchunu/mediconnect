from django.urls import path
from .views import (
    BookAppointmentView, CalendarView, AppointmentListView, 
    AppointmentDetailView, RescheduleAppointmentView,
    cancel_appointment, complete_appointment, appointment_dashboard
)

app_name = 'appointments'

urlpatterns = [
    path('', appointment_dashboard, name='dashboard'),
    path('book/<int:referral_id>/', BookAppointmentView.as_view(), name='book'),
    path('calendar/', CalendarView.as_view(), name='calendar'),
    path('list/', AppointmentListView.as_view(), name='list'),
    path('<int:pk>/', AppointmentDetailView.as_view(), name='detail'),
    path('<int:pk>/reschedule/', RescheduleAppointmentView.as_view(), name='reschedule'),
    path('<int:pk>/cancel/', cancel_appointment, name='cancel'),
    path('<int:pk>/complete/', complete_appointment, name='complete'),
]