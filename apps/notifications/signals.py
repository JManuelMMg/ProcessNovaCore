from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.sales.models import Sale
from apps.inventory.models import Stock
from apps.crm.models import Lead, Opportunity
from apps.hr.models import LeaveRequest
from apps.logistics.models import Shipment
from .models import Notification


@receiver(post_save, sender=Sale)
def create_sale_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            organization=instance.organization,
            type='sale',
            channel='in_app',
            priority='medium',
            title=f'Venta creada: {instance.number}',
            message=f'Se ha registrado una venta por ${instance.total}',
            link=f'/sales/{instance.pk}/',
            related_type='sale',
            related_id=instance.pk,
            status='read'
        )


@receiver(post_save, sender=Stock)
def create_stock_alert_notification(sender, instance, **kwargs):
    if instance.quantity <= instance.min_quantity:
        Notification.objects.create(
            organization=instance.organization,
            type='stock_alert',
            channel='in_app',
            priority='high',
            title=f'Alerta de stock bajo: {instance.product.name}',
            message=f'El producto {instance.product.name} tiene {instance.quantity} unidades, mínimo recomendado {instance.min_quantity}',
            link='/inventory/stocks/',
            related_type='stock',
            related_id=instance.pk,
            status='pending'
        )


@receiver(post_save, sender=Lead)
def create_lead_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            organization=instance.organization,
            type='lead',
            channel='in_app',
            priority='medium',
            title=f'Nuevo lead: {instance.name}',
            message=f'Se ha registrado un nuevo lead: {instance.name}',
            link=f'/crm/leads/{instance.pk}/',
            related_type='lead',
            related_id=instance.pk,
            status='read'
        )


@receiver(post_save, sender=Opportunity)
def create_opportunity_notification(sender, instance, created, **kwargs):
    if instance.status == 'won' or instance.status == 'closed_won':
        Notification.objects.create(
            organization=instance.organization,
            type='opportunity',
            channel='in_app',
            priority='high',
            title=f'Oportunidad ganada: {instance.title}',
            message=f'La oportunidad {instance.title} ha sido cerrada como ganada!',
            link='/crm/opportunities/',
            related_type='opportunity',
            related_id=instance.pk,
            status='read'
        )


@receiver(post_save, sender=LeaveRequest)
def create_leave_request_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            organization=instance.organization,
            type='leave_request',
            channel='in_app',
            priority='medium',
            title=f'Nueva solicitud de permiso: {instance.employee}',
            message=f'{instance.employee} ha solicitado permiso desde {instance.start_date} hasta {instance.end_date}',
            link=f'/hr/employees/{instance.employee.pk}/',
            related_type='leave_request',
            related_id=instance.pk,
            status='pending'
        )


@receiver(post_save, sender=Shipment)
def create_shipment_notification(sender, instance, **kwargs):
    if instance.status == 'delivered':
        Notification.objects.create(
            organization=instance.organization,
            type='shipment',
            channel='in_app',
            priority='medium',
            title=f'Envío entregado: {instance.tracking_number}',
            message=f'El envío {instance.tracking_number} ha sido entregado exitosamente!',
            link=f'/logistics/shipments/{instance.pk}/',
            related_type='shipment',
            related_id=instance.pk,
            status='read'
        )
    elif instance.status in ['failed', 'returned']:
        Notification.objects.create(
            organization=instance.organization,
            type='shipment',
            channel='in_app',
            priority='high',
            title=f'Problema con envío: {instance.tracking_number}',
            message=f'El envío {instance.tracking_number} tiene estado: {instance.status}',
            link=f'/logistics/shipments/{instance.pk}/',
            related_type='shipment',
            related_id=instance.pk,
            status='pending'
        )
