from django.contrib import admin
from .models import (
    Department, Position, Employee, Attendance, LeaveRequest,
    Benefit, EmployeeBenefit, PerformanceReview, Payroll
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'manager', 'organization')
    list_filter = ('organization',)
    search_fields = ('name',)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'organization')
    list_filter = ('organization', 'department')
    search_fields = ('title',)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'position', 'department', 'hire_date', 'status', 'organization')
    list_filter = ('organization', 'status', 'department', 'hire_date')
    search_fields = ('first_name', 'last_name', 'email', 'phone')

    def full_name(self, obj):
        return obj.full_name


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'status', 'check_in', 'check_out', 'worked_hours', 'organization')
    list_filter = ('organization', 'status', 'date')
    search_fields = ('employee__first_name', 'employee__last_name')
    readonly_fields = ('worked_hours', 'overtime_hours')


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'type', 'start_date', 'end_date', 'days', 'status', 'organization')
    list_filter = ('organization', 'status', 'type', 'start_date')
    search_fields = ('employee__first_name', 'employee__last_name')


@admin.register(Benefit)
class BenefitAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'is_active', 'organization')
    list_filter = ('organization', 'type', 'is_active')
    search_fields = ('name',)


@admin.register(EmployeeBenefit)
class EmployeeBenefitAdmin(admin.ModelAdmin):
    list_display = ('employee', 'benefit', 'start_date', 'is_active', 'organization')
    list_filter = ('organization', 'is_active', 'benefit')
    search_fields = ('employee__first_name', 'employee__last_name')


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ('employee', 'review_date', 'overall_rating', 'status', 'organization')
    list_filter = ('organization', 'status', 'review_date')
    search_fields = ('employee__first_name', 'employee__last_name')


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 'period_start', 'period_end', 'gross_salary', 
        'total_deductions', 'net_salary', 'status', 'organization'
    )
    list_filter = ('organization', 'status', 'period_start')
    search_fields = ('employee__first_name', 'employee__last_name')

