from django.db import models
from core.models import TenantAwareModel
from auditlog.registry import auditlog
from datetime import time, datetime, timedelta


class Department(TenantAwareModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    manager = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_departments')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Position(TenantAwareModel):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='positions')
    level = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Employee(TenantAwareModel):
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, related_name='employee', null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(unique=True)
    personal_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    mobile_phone = models.CharField(max_length=20, blank=True)
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    hire_date = models.DateField()
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Masculino'), ('female', 'Femenino'), ('other', 'Otro')], blank=True)
    marital_status = models.CharField(max_length=20, choices=[('single', 'Soltero'), ('married', 'Casado'), ('divorced', 'Divorciado'), ('widowed', 'Viudo')], blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    rfc = models.CharField(max_length=13, blank=True)
    nss = models.CharField(max_length=11, blank=True)
    curp = models.CharField(max_length=18, blank=True)
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relationship = models.CharField(max_length=100, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2)
    payment_frequency = models.CharField(max_length=20, choices=[('weekly', 'Semanal'), ('biweekly', 'Quincenal'), ('monthly', 'Mensual')], default='biweekly')
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=50, blank=True)
    clabe = models.CharField(max_length=18, blank=True)
    status = models.CharField(max_length=20, choices=[('active', 'Activo'), ('inactive', 'Inactivo'), ('on_leave', 'En permiso'), ('terminated', 'Terminado')], default='active')
    termination_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.position.title if self.position else 'Sin puesto'}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.middle_name + ' ' if self.middle_name else ''}{self.last_name}"
    
    @property
    def years_of_service(self):
        return (datetime.now().date() - self.hire_date).days // 365


class Attendance(TenantAwareModel):
    STATUS_CHOICES = [
        ('present', 'Presente'),
        ('absent', 'Ausente'),
        ('late', 'Tarde'),
        ('excused', 'Justificado'),
        ('vacation', 'Vacaciones'),
        ('holiday', 'Día festivo'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['employee', 'date', 'organization']
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee.full_name} - {self.date}: {self.get_status_display()}"
    
    @property
    def worked_hours(self):
        if self.check_in and self.check_out:
            check_in_datetime = datetime.combine(self.date, self.check_in)
            check_out_datetime = datetime.combine(self.date, self.check_out)
            return (check_out_datetime - check_in_datetime).total_seconds() / 3600
        return 0
    
    @property
    def overtime_hours(self):
        if self.worked_hours > 8:
            return self.worked_hours - 8
        return 0


class LeaveRequest(TenantAwareModel):
    TYPE_CHOICES = [
        ('vacation', 'Vacaciones'),
        ('sick', 'Enfermedad'),
        ('personal', 'Personal'),
        ('maternity', 'Maternidad'),
        ('paternity', 'Paternidad'),
        ('bereavement', 'Duelo'),
        ('other', 'Otro'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('cancelled', 'Cancelado'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.full_name} - {self.get_type_display()} ({self.start_date} a {self.end_date})"


class Benefit(TenantAwareModel):
    TYPE_CHOICES = [
        ('health_insurance', 'Seguro médico'),
        ('life_insurance', 'Seguro de vida'),
        ('retirement', 'Ahorro para retiro'),
        ('bonus', 'Bono'),
        ('meal_vouchers', 'Vales de comida'),
        ('transport', 'Transporte'),
        ('other', 'Otro'),
    ]

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class EmployeeBenefit(TenantAwareModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='benefits')
    benefit = models.ForeignKey(Benefit, on_delete=models.CASCADE, related_name='employees')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    employee_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    employer_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.employee.full_name} - {self.benefit.name}"


class PerformanceReview(TenantAwareModel):
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('pending', 'Pendiente'),
        ('completed', 'Completada'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='conducted_reviews')
    review_date = models.DateField()
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    overall_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, help_text="Calificación 1-5")
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    goals = models.TextField(blank=True)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Revisión {self.employee.full_name} - {self.review_date}"


class Payroll(TenantAwareModel):
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('approved', 'Aprobado'),
        ('paid', 'Pagada'),
        ('cancelled', 'Cancelado'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payrolls')
    period_start = models.DateField()
    period_end = models.DateField()
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    daily_salary = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    worked_days = models.IntegerField(default=0)
    regular_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    overtime_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonuses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commissions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    isr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    imss = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    infonavit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Nómina {self.employee.full_name} - {self.period_start} a {self.period_end}"
    
    def calculate_totals(self):
        if self.base_salary and self.worked_days > 0:
            self.daily_salary = self.base_salary / 30
            regular_pay = self.daily_salary * self.worked_days
            self.gross_salary = regular_pay + self.overtime_pay + self.bonuses + self.commissions + self.allowances
            self.total_deductions = self.isr + self.imss + self.infonavit + self.other_deductions
            self.net_salary = self.gross_salary - self.total_deductions
            self.save()


auditlog.register(Department)
auditlog.register(Position)
auditlog.register(Employee)
auditlog.register(Attendance)
auditlog.register(LeaveRequest)
auditlog.register(Benefit)
auditlog.register(EmployeeBenefit)
auditlog.register(PerformanceReview)
auditlog.register(Payroll)

