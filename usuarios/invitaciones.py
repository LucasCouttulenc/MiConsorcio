import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse

from config.comun import GRUPO_PROPIETARIOS, PERMISOS_PROPIETARIOS
from .models import InvitacionPropietario, Propietario


DIAS_VALIDEZ_INVITACION = 7


def hash_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def usuarios_para_correo(email):
    return get_user_model().objects.filter(
        Q(email__iexact=email.strip()) | Q(username__iexact=email.strip())
    ).distinct()


def vincular_propietario(unidad, usuario, invitacion=None):
    """Asigna la UF a la cuenta (creando su Propietario si hace falta) y cierra la invitación."""
    propietario, _ = Propietario.objects.get_or_create(usuario=usuario)
    if unidad.propietario_id and unidad.propietario_id != propietario.pk:
        raise ValueError('Esta unidad ya fue vinculada a otra cuenta.')
    unidad.propietario = propietario
    unidad.save(update_fields=['propietario'])
    if invitacion is None:
        invitacion = InvitacionPropietario.objects.filter(unidad_funcional=unidad).first()
    if invitacion:
        invitacion.aceptada = timezone.now()
        invitacion.save(update_fields=['aceptada'])

    grupo, _ = Group.objects.get_or_create(name=GRUPO_PROPIETARIOS)
    permisos = Permission.objects.filter(codename__in=PERMISOS_PROPIETARIOS)
    grupo.permissions.add(*permisos)
    usuario.groups.add(grupo)

    # Las liquidaciones cerradas mientras la UF estaba pendiente también son nuevas para su propietario.
    from gastos.models import DetalleLiquidacionUF, NotificacionLiquidacion
    NotificacionLiquidacion.objects.bulk_create([
        NotificacionLiquidacion(propietario=propietario, detalle_liquidacion=detalle)
        for detalle in DetalleLiquidacionUF.objects.filter(
            unidad_funcional=unidad, liquidacion__cerrada=True,
        )
    ], ignore_conflicts=True)


def vincular_pendientes_del_correo(usuario, email):
    """Al crear la cuenta, suma también las otras UF que tenían invitación pendiente a ese correo."""
    pendientes = InvitacionPropietario.objects.select_related('unidad_funcional').filter(
        email__iexact=email, aceptada__isnull=True, unidad_funcional__propietario__isnull=True,
    )
    for invitacion in pendientes:
        vincular_propietario(invitacion.unidad_funcional, usuario, invitacion)


def asignar_propietario(unidad, email, request):
    """
    Si el correo ya tiene una cuenta, suma la UF directo (sin link); si no, le manda la invitación
    para que cree su cuenta. Devuelve 'vinculada' o 'invitada'.
    """
    coincidencias = list(usuarios_para_correo(email)[:2])
    if len(coincidencias) == 1 and coincidencias[0].is_active:
        with transaction.atomic():
            vincular_propietario(unidad, coincidencias[0])
        return 'vinculada'
    enviar_invitacion_propietario(unidad, email, request)
    return 'invitada'


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
