import uuid
from decimal import Decimal
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from django.utils import timezone


IVA_RATE = Decimal('16')


def _fmt(value):
    return f"{Decimal(value):.2f}"


def generate_cfdi_xml(invoice, organization):
    """Genera XML CFDI 4.0 (estructura base, listo para timbrado con PAC)."""
    root = Element('cfdi:Comprobante', {
        'xmlns:cfdi': 'http://www.sat.gob.mx/cfd/4',
        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'Version': '4.0',
        'Serie': invoice.serie,
        'Folio': str(invoice.folio),
        'Fecha': invoice.date.isoformat() + 'T12:00:00',
        'SubTotal': _fmt(invoice.subtotal),
        'Total': _fmt(invoice.total),
        'Moneda': 'MXN',
        'TipoDeComprobante': invoice.tipo_comprobante,
        'Exportacion': '01',
        'MetodoPago': invoice.metodo_pago,
        'FormaPago': invoice.forma_pago,
        'LugarExpedicion': organization.codigo_postal,
    })

    emisor = SubElement(root, 'cfdi:Emisor', {
        'Rfc': organization.rfc,
        'Nombre': organization.razon_social,
        'RegimenFiscal': organization.regimen_fiscal,
    })

    receptor_rfc = invoice.customer.rfc or 'XAXX010101000'
    receptor = SubElement(root, 'cfdi:Receptor', {
        'Rfc': receptor_rfc,
        'Nombre': invoice.customer.name,
        'UsoCFDI': invoice.uso_cfdi,
        'DomicilioFiscalReceptor': organization.codigo_postal,
        'RegimenFiscalReceptor': '616',
    })

    conceptos = SubElement(root, 'cfdi:Conceptos')
    for item in invoice.items.all():
        SubElement(conceptos, 'cfdi:Concepto', {
            'ClaveProdServ': item.clave_prod_serv,
            'Cantidad': _fmt(item.quantity),
            'ClaveUnidad': item.clave_unidad,
            'Descripcion': item.description[:1000],
            'ValorUnitario': _fmt(item.unit_price),
            'Importe': _fmt(item.subtotal),
            'ObjetoImp': '02',
        })

    impuestos = SubElement(root, 'cfdi:Impuestos', {
        'TotalImpuestosTrasladados': _fmt(invoice.tax),
    })
    traslados = SubElement(impuestos, 'cfdi:Traslados')
    SubElement(traslados, 'cfdi:Traslado', {
        'Base': _fmt(invoice.subtotal),
        'Impuesto': '002',
        'TipoFactor': 'Tasa',
        'TasaOCuota': '0.160000',
        'Importe': _fmt(invoice.tax),
    })

    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding='unicode')
    return xml_str


def stamp_cfdi(invoice, organization):
    """
    Simula timbrado CFDI generando UUID y XML.
    En producción, enviar xml a un PAC (Finkok, SW Sapien, etc.).
    """
    if not invoice.items.exists():
        raise ValueError('La factura no tiene conceptos')

    xml = generate_cfdi_xml(invoice, organization)
    cfdi_uuid = str(uuid.uuid4()).upper()

    invoice.xml_content = xml
    invoice.cfdi_uuid = cfdi_uuid
    invoice.cfdi_status = 'stamped'
    invoice.status = 'stamped'
    invoice.stamped_at = timezone.now()
    invoice.save()

    return {
        'uuid': cfdi_uuid,
        'xml': xml,
        'stamped_at': invoice.stamped_at.isoformat(),
    }


def create_invoice_from_sale(sale, customer, organization):
    from .models import Invoice, InvoiceItem

    last = Invoice.objects.filter(organization=organization).order_by('-folio').first()
    folio = (last.folio + 1) if last else 1
    number = f"{organization.rfc[:3].upper()}-{folio:06d}"

    payment = sale.payments.first()
    forma_pago_map = {
        'cash': '01',
        'card_debit': '04',
        'card_credit': '04',
        'transfer': '03',
        'spei': '03',
        'check': '02',
        'loyalty_points': '99',
        'credit_note': '17',
    }

    invoice = Invoice.objects.create(
        organization=organization,
        sale=sale,
        customer=customer,
        number=number,
        folio=folio,
        date=timezone.now().date(),
        subtotal=sale.subtotal,
        tax=sale.subtotal * (IVA_RATE / 100),
        total=sale.subtotal * (1 + IVA_RATE / 100),
        forma_pago=forma_pago_map.get(payment.method if payment else 'cash', '01'),
        metodo_pago='PUE',
        uso_cfdi='G03',
    )

    for item in sale.items.select_related('product').all():
        InvoiceItem.objects.create(
            organization=organization,
            invoice=invoice,
            product=item.product,
            description=item.product.name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            tax_rate=IVA_RATE,
        )

    invoice.calculate_totals()
    return invoice
