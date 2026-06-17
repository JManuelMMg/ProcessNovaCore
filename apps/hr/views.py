from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from core.permissions import permission_required, tenant_required
from .models import Employee
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
