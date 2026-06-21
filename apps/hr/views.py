from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta

from core.permissions import permission_required, tenant_required
from .models import Employee, Attendance, LeaveRequest, Payroll
from .forms import EmployeeForm


@login_required
@tenant_required
@permission_required('hr_view')
def employee_list(request):
    employees = Employee.objects.for_org(request.organization).select_related('position', 'department')
    return render(request, 'hr/employee_list.html', {'employees': employees})


@login_required
@tenant_required
@permission_required('hr_view')
def employee_detail(request, pk):
    employee = get_object_or_404(Employee.objects.for_org(request.organization).select_related('position', 'department'), pk=pk)
    return render(request, 'hr/employee_detail.html', {'employee': employee})


@login_required
@tenant_required
@permission_required('hr_create')
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST, organization=request.organization)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.organization = request.organization
            employee.save()
            messages.success(request, 'Empleado creado exitosamente!')
            return redirect('hr:employee_detail', pk=employee.pk)
    else:
        form = EmployeeForm(organization=request.organization)
    return render(request, 'hr/employee_form.html', {'form': form, 'editing': False})


@login_required
@tenant_required
@permission_required('hr_edit')
def employee_edit(request, pk):
    employee = get_object_or_404(Employee.objects.for_org(request.organization), pk=pk)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee, organization=request.organization)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empleado actualizado exitosamente!')
            return redirect('hr:employee_detail', pk=employee.pk)
    else:
        form = EmployeeForm(instance=employee, organization=request.organization)
    return render(request, 'hr/employee_form.html', {'form': form, 'editing': True, 'employee': employee})


@login_required
@tenant_required
@permission_required('hr_view')
def department_list(request):
    return render(request, 'hr/department_list.html')


@login_required
@tenant_required
@permission_required('hr_view')
def hr_analytics(request):
    """HR analytics view."""
    today = timezone.localdate()
    start_month = today - timedelta(days=30)

    employees = Employee.objects.for_org(request.organization)
    total_employees = employees.count()
    active_employees = employees.filter(status='active').count()

    attendances = Attendance.objects.for_org(request.organization).filter(date__gte=start_month)
    total_attendances = attendances.count()
    late_attendances = attendances.filter(status='late').count()
    absent_attendances = attendances.filter(status='absent').count()

    leave_requests = LeaveRequest.objects.for_org(request.organization).filter(created_at__date__gte=start_month)
    total_leaves = leave_requests.count()
    pending_leaves = leave_requests.filter(status='pending').count()

    payrolls = Payroll.objects.for_org(request.organization).filter(period_end__gte=start_month)
    total_payroll = payrolls.aggregate(Sum('net_salary'))['net_salary__sum'] or 0

    return render(request, 'hr/analytics.html', {
        'total_employees': total_employees,
        'active_employees': active_employees,
        'total_attendances': total_attendances,
        'late_attendances': late_attendances,
        'absent_attendances': absent_attendances,
        'total_leaves': total_leaves,
        'pending_leaves': pending_leaves,
        'total_payroll': float(total_payroll)
    })


@login_required
@tenant_required
@permission_required('hr_view')
@require_GET
def api_hr_stats(request):
    """HR analytics API endpoint."""
    today = timezone.localdate()
    start_month = today - timedelta(days=30)

    employees = Employee.objects.for_org(request.organization)
    total_employees = employees.count()
    active_employees = employees.filter(status='active').count()

    attendances = Attendance.objects.for_org(request.organization).filter(date__gte=start_month)
    total_attendances = attendances.count()
    late_attendances = attendances.filter(status='late').count()
    absent_attendances = attendances.filter(status='absent').count()

    leave_requests = LeaveRequest.objects.for_org(request.organization).filter(created_at__date__gte=start_month)
    total_leaves = leave_requests.count()
    pending_leaves = leave_requests.filter(status='pending').count()

    payrolls = Payroll.objects.for_org(request.organization).filter(period_end__gte=start_month)
    total_payroll = payrolls.aggregate(Sum('net_salary'))['net_salary__sum'] or 0

    return JsonResponse({
        'total_employees': total_employees,
        'active_employees': active_employees,
        'total_attendances': total_attendances,
        'late_attendances': late_attendances,
        'absent_attendances': absent_attendances,
        'total_leaves': total_leaves,
        'pending_leaves': pending_leaves,
        'total_payroll': float(total_payroll)
    })
