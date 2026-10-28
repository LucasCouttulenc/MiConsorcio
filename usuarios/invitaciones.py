import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse

from .models import InvitacionPropietario


DIAS_VALIDEZ_INVITACION = 7


def hash_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def enviar_invitacion_propietario(unidad, email, request):
    """Crea o renueva el enlace y lo envía al correo indicado."""
    invitacion, _ = InvitacionPropietario.objects.get_or_create(
        unidad_funcional=unidad,
        defaults={
            'email': email,
            'token_hash': secrets.token_hex(32),
            'expira': timezone.now(),
        },
    )
    token = secrets.token_urlsafe(32)
    invitacion.email = email.strip().lower()
    invitacion.token_hash = hash_token(token)
    invitacion.expira = timezone.now() + timedelta(days=DIAS_VALIDEZ_INVITACION)
    invitacion.enviada = None
    invitacion.aceptada = None
    invitacion.save(update_fields=['email', 'token_hash', 'expira', 'enviada', 'aceptada'])

    url = request.build_absolute_uri(
        reverse('aceptar_invitacion_propietario', kwargs={'token': token})
    )
    etiqueta_uf = f"Piso {unidad.piso}" + (f" · Depto. {unidad.departamento}" if unidad.departamento else '')
    texto = (
        f"Te invitaron a vincular {etiqueta_uf} del consorcio {unidad.consorcio.nombre} "
        f"a tu cuenta de MiConsorcios. Abrí este enlace para continuar: {url}\n\n"
        f"El enlace vence en {DIAS_VALIDEZ_INVITACION} días."
    )
    html = format_html(
        '<p>Te invitaron a vincular una unidad funcional a tu cuenta de MiConsorcios.</p>'
        '<p><strong>{}</strong><br>{}</p>'
        '<p><a href="{}" style="display:inline-block;padding:12px 20px;background:#3b82f6;'
        'color:#ffffff;text-decoration:none;border-radius:8px;font-weight:700">'
        'Unirme a esta unidad</a></p>'
        '<p>El enlace vence en {} días. Si no esperabas esta invitación, podés ignorar este correo.</p>',
        unidad.consorcio.nombre, etiqueta_uf, url, DIAS_VALIDEZ_INVITACION,
    )
    enviados = send_mail(
        subject=f"Invitación a {unidad.consorcio.nombre} en MiConsorcios",
        message=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invitacion.email],
        html_message=html,
        fail_silently=False,
    )
    if enviados != 1:
        raise RuntimeError('El servidor de correo no aceptó el mensaje.')

    invitacion.enviada = timezone.now()
    invitacion.save(update_fields=['enviada'])
    return invitacion
