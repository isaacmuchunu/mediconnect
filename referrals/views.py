from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from .models import Referral
from .forms import ReferralForm, ReferralSearchForm, ReferralResponseForm, ReferralUpdateForm
from patients.models import Patient
from doctors.models import DoctorProfile

class CreateReferralView(LoginRequiredMixin, CreateView):
    model = Referral
    form_class = ReferralForm
    template_name = 'referrals/create_referral.html'
    success_url = reverse_lazy('referrals:list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.referring_doctor = self.request.user.doctor_profile
        messages.success(self.request, 'Referral created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patients'] = Patient.objects.all()
        context['doctors'] = DoctorProfile.objects.exclude(user=self.request.user)
        return context

class ReferralDetailView(LoginRequiredMixin, DetailView):
    model = Referral
    template_name = 'referrals/referral_detail.html'
    context_object_name = 'referral'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['response_form'] = ReferralResponseForm()
        context['update_form'] = ReferralUpdateForm(instance=self.object)
        
        # Mark as viewed if target doctor is viewing
        if (hasattr(self.request.user, 'doctor_profile') and 
            self.object.target_doctor == self.request.user.doctor_profile and 
            self.object.status == 'sent'):
            self.object.status = 'viewed'
            self.object.viewed_at = timezone.now()
            self.object.save()
        
        return context

class ListReferralsView(LoginRequiredMixin, ListView):
    model = Referral
    template_name = 'referrals/referral_list.html'
    context_object_name = 'referrals'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Referral.objects.all()
        
        # Filter based on user role
        if hasattr(self.request.user, 'doctor_profile'):
            doctor = self.request.user.doctor_profile
            view_type = self.request.GET.get('view', 'sent')
            
            if view_type == 'received':
                queryset = queryset.filter(target_doctor=doctor)
            else:
                queryset = queryset.filter(referring_doctor=doctor)
        
        # Apply search filters
        form = ReferralSearchForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data['status']:
                queryset = queryset.filter(status=form.cleaned_data['status'])
            if form.cleaned_data['priority']:
                queryset = queryset.filter(priority=form.cleaned_data['priority'])
            if form.cleaned_data['specialty']:
                queryset = queryset.filter(specialty__icontains=form.cleaned_data['specialty'])
            if form.cleaned_data['patient_name']:
                queryset = queryset.filter(
                    Q(patient__user__first_name__icontains=form.cleaned_data['patient_name']) |
                    Q(patient__user__last_name__icontains=form.cleaned_data['patient_name'])
                )
            if form.cleaned_data['doctor_name']:
                queryset = queryset.filter(
                    Q(referring_doctor__user__first_name__icontains=form.cleaned_data['doctor_name']) |
                    Q(referring_doctor__user__last_name__icontains=form.cleaned_data['doctor_name']) |
                    Q(target_doctor__user__first_name__icontains=form.cleaned_data['doctor_name']) |
                    Q(target_doctor__user__last_name__icontains=form.cleaned_data['doctor_name'])
                )
            if form.cleaned_data['date_from']:
                queryset = queryset.filter(created_at__date__gte=form.cleaned_data['date_from'])
            if form.cleaned_data['date_to']:
                queryset = queryset.filter(created_at__date__lte=form.cleaned_data['date_to'])
        
        return queryset.select_related('patient__user', 'referring_doctor__user', 'target_doctor__user')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = ReferralSearchForm(self.request.GET)
        context['view_type'] = self.request.GET.get('view', 'sent')
        
        # Add statistics
        if hasattr(self.request.user, 'doctor_profile'):
            doctor = self.request.user.doctor_profile
            context['stats'] = {
                'total_sent': Referral.objects.filter(referring_doctor=doctor).count(),
                'total_received': Referral.objects.filter(target_doctor=doctor).count(),
                'pending_response': Referral.objects.filter(
                    target_doctor=doctor, 
                    status__in=['sent', 'viewed']
                ).count(),
                'urgent_referrals': Referral.objects.filter(
                    Q(referring_doctor=doctor) | Q(target_doctor=doctor),
                    priority='urgent',
                    status__in=['sent', 'viewed']
                ).count()
            }
        
        return context

@login_required
def accept_referral(request, referral_id):
    referral = get_object_or_404(Referral, id=referral_id)
    
    if hasattr(request.user, 'doctor_profile') and referral.target_doctor == request.user.doctor_profile:
        referral.status = 'accepted'
        referral.responded_at = timezone.now()
        referral.save()
        messages.success(request, 'Referral accepted successfully!')
    else:
        messages.error(request, 'You are not authorized to accept this referral.')
    
    return redirect('referrals:detail', pk=referral.id)

@login_required
def decline_referral(request, referral_id):
    referral = get_object_or_404(Referral, id=referral_id)
    
    if hasattr(request.user, 'doctor_profile') and referral.target_doctor == request.user.doctor_profile:
        if request.method == 'POST':
            form = ReferralResponseForm(request.POST)
            if form.is_valid():
                referral.status = 'declined'
                referral.response_notes = form.cleaned_data['response_notes']
                referral.responded_at = timezone.now()
                referral.save()
                messages.success(request, 'Referral declined with notes.')
                return redirect('referrals:detail', pk=referral.id)
        else:
            form = ReferralResponseForm()
        
        return render(request, 'referrals/decline_referral.html', {
            'referral': referral,
            'form': form
        })
    else:
        messages.error(request, 'You are not authorized to decline this referral.')
        return redirect('referrals:detail', pk=referral.id)

@login_required
def complete_referral(request, referral_id):
    referral = get_object_or_404(Referral, id=referral_id)
    
    if (hasattr(request.user, 'doctor_profile') and 
        referral.target_doctor == request.user.doctor_profile and 
        referral.status == 'accepted'):
        
        if request.method == 'POST':
            form = ReferralResponseForm(request.POST)
            if form.is_valid():
                referral.status = 'completed'
                referral.response_notes = form.cleaned_data['response_notes']
                referral.responded_at = timezone.now()
                referral.save()
                messages.success(request, 'Referral marked as completed!')
                return redirect('referrals:detail', pk=referral.id)
        else:
            form = ReferralResponseForm()
        
        return render(request, 'referrals/complete_referral.html', {
            'referral': referral,
            'form': form
        })
    else:
        messages.error(request, 'You are not authorized to complete this referral.')
        return redirect('referrals:detail', pk=referral.id)

@login_required
def referral_dashboard(request):
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, 'Access denied. Doctor profile required.')
        return redirect('home')
    
    doctor = request.user.doctor_profile
    
    # Get statistics
    stats = {
        'total_sent': Referral.objects.filter(referring_doctor=doctor).count(),
        'total_received': Referral.objects.filter(target_doctor=doctor).count(),
        'pending_sent': Referral.objects.filter(
            referring_doctor=doctor, 
            status__in=['sent', 'viewed']
        ).count(),
        'pending_received': Referral.objects.filter(
            target_doctor=doctor, 
            status__in=['sent', 'viewed']
        ).count(),
        'urgent_referrals': Referral.objects.filter(
            Q(referring_doctor=doctor) | Q(target_doctor=doctor),
            priority='urgent',
            status__in=['sent', 'viewed']
        ).count()
    }
    
    # Recent referrals
    recent_sent = Referral.objects.filter(referring_doctor=doctor).order_by('-created_at')[:5]
    recent_received = Referral.objects.filter(target_doctor=doctor).order_by('-created_at')[:5]
    
    # Urgent referrals
    urgent_referrals = Referral.objects.filter(
        Q(referring_doctor=doctor) | Q(target_doctor=doctor),
        priority='urgent',
        status__in=['sent', 'viewed']
    ).order_by('-created_at')[:10]
    
    context = {
        'stats': stats,
        'recent_sent': recent_sent,
        'recent_received': recent_received,
        'urgent_referrals': urgent_referrals,
    }
    
    return render(request, 'referrals/dashboard.html', context)