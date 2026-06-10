from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def employee_list(request):
    return render(request, 'hr/employee_list.html')


@login_required
def employee_detail(request, pk):
    return render(request, 'hr/employee_detail.html')


@login_required
def department_list(request):
    return render(request, 'hr/department_list.html')
