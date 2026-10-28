from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, Permission
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme

from config.comun import GRUPO_PROPIETARIOS, PERMISOS_PROPIETARIOS
from consorcios.permisos import consorcios_permitidos
from .forms import FormularioLogin, FormularioRegistroPropietario
from .invitaciones import hash_token
from .models import InvitacionPropietario, Propietario


def pagina_inicial(usuario):
    """El propietario arranca en su Inicio; el resto, en la bienvenida."""
    if Propietario.objects.filter(usuario=usuario).exists():
        return redirect('inicio_propietario')
    return redirect('bienvenida')

def login(request):
    if request.user.is_authenticated:
        return pagina_inicial(request.user)
    elif request.method == 'POST':
        formulario = FormularioLogin(request=request, data=request.POST)
        if formulario.is_valid():
            usuario = formulario.get_user()
            auth_login(request, usuario)
            return pagina_inicial(usuario)
    else:
        formulario = FormularioLogin()
    return render(request, 'login.html', {'formulario': formulario})

@login_required
def bienvenida(request):
    return render(request, 'bienvenida.html')


def _usuarios_para_correo(email):
    User = get_user_model()
    return User.objects.filter(
        Q(email__iexact=email) | Q(username__iexact=email)
    ).distinct()


def _vincular_propietario(unidad, usuario, invitacion):
    propietario, _ = Propietario.objects.get_or_create(usuario=usuario)
    if unidad.propietario_id and unidad.propietario_id != propietario.pk:
        raise ValueError('Esta unidad ya fue vinculada a otra cuenta.')
    unidad.propietario = propietario
    unidad.save(update_fields=['propietario'])
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


def aceptar_invitacion_propietario(request, token):
    """Vincula una UF existente o registra la primera cuenta de su propietario."""
    invitacion = get_object_or_404(
        InvitacionPropietario.objects.select_related(
            'unidad_funcional__consorcio', 'unidad_funcional__propietario__usuario',
        ),
        token_hash=hash_token(token),
    )
    if invitacion.aceptada:
        return render(request, 'aceptar_invitacion_propietario.html', {
            'ya_aceptada': True,
            'unidad': invitacion.unidad_funcional,
        }, status=410)
    if invitacion.expira <= timezone.now():
        return render(request, 'aceptar_invitacion_propietario.html', {
            'vencida': True,
            'unidad': invitacion.unidad_funcional,
        }, status=410)

    coincidencias = _usuarios_para_correo(invitacion.email)
    if coincidencias.count() > 1:
        return render(request, 'aceptar_invitacion_propietario.html', {
            'error_invitacion': 'No pudimos identificar una única cuenta para este correo. Contactá a la administración.',
            'unidad': invitacion.unidad_funcional,
        }, status=409)

    if coincidencias.exists():
        usuario = coincidencias.first()
        if not usuario.is_active:
            return render(request, 'aceptar_invitacion_propietario.html', {
                'error_invitacion': 'La cuenta asociada está desactivada. Contactá a la administración.',
                'unidad': invitacion.unidad_funcional,
            }, status=403)
        try:
            with transaction.atomic():
                invitacion = InvitacionPropietario.objects.select_for_update().select_related(
                    'unidad_funcional',
                ).get(pk=invitacion.pk)
                if invitacion.aceptada or invitacion.expira <= timezone.now():
                    raise ValueError('El enlace ya fue usado o venció.')
                _vincular_propietario(invitacion.unidad_funcional, usuario, invitacion)
        except ValueError as error:
            return render(request, 'aceptar_invitacion_propietario.html', {
                'error_invitacion': str(error), 'unidad': invitacion.unidad_funcional,
            }, status=409)
        auth_login(request, usuario, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, 'La unidad funcional ya está vinculada a tu cuenta.')
        return redirect('inicio_propietario')

    formulario = FormularioRegistroPropietario(
        request.POST if request.method == 'POST' else None,
        email=invitacion.email,
    )
    if request.method == 'POST' and formulario.is_valid():
        User = get_user_model()
        try:
            with transaction.atomic():
                invitacion = InvitacionPropietario.objects.select_for_update().select_related(
                    'unidad_funcional',
                ).get(pk=invitacion.pk)
                if invitacion.aceptada or invitacion.expira <= timezone.now():
                    raise ValueError('El enlace ya fue usado o venció.')

                # Otra cuenta podría haberse creado mientras el formulario estaba abierto.
                existentes = _usuarios_para_correo(invitacion.email)
                if existentes.count() > 1:
                    raise ValueError('No pudimos identificar una única cuenta para este correo.')
                if existentes.exists():
                    usuario = existentes.first()
                else:
                    email = invitacion.email.strip().lower()
                    if User.objects.filter(username__iexact=email).exists():
                        formulario.add_error('email', 'Este correo ya está asociado a otra cuenta. Contactá a la administración.')
                        raise ValueError('El usuario ya existe con otro correo.')
                    usuario = User.objects.create_user(
                        username=email,
                        email=email,
                        first_name=formulario.cleaned_data['nombre'].strip(),
                        last_name=formulario.cleaned_data['apellido'].strip(),
                        password=formulario.cleaned_data['password'],
                    )
                if not usuario.is_active:
                    raise ValueError('La cuenta asociada está desactivada. Contactá a la administración.')
                _vincular_propietario(invitacion.unidad_funcional, usuario, invitacion)
        except ValueError as error:
            if not formulario.errors:
                formulario.add_error(None, str(error))
        except IntegrityError:
            formulario.add_error('email', 'Ya se creó una cuenta con este correo. Volvé a abrir la invitación para vincularla.')
        else:
            auth_login(request, usuario, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Tu cuenta quedó vinculada a la unidad funcional.')
            return redirect('inicio_propietario')

    return render(request, 'aceptar_invitacion_propietario.html', {
        'formulario': formulario,
        'unidad': invitacion.unidad_funcional,
    })




@login_required
@require_POST
def cambiar_consorcio_activo(request):
    """Cambia el consorcio activo desde el selector del sidebar, solo a uno que el usuario administre."""
    consorcio_id = request.POST.get('consorcio_id', '')
    consorcio = consorcios_permitidos(request.user).filter(pk=consorcio_id).first() if consorcio_id.isdecimal() else None
    if consorcio:
        request.session['consorcio_activo_id'] = consorcio.pk
    else:
        messages.error(request, "No tenés acceso a ese consorcio.")

    destino = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        destino = 'bienvenida'
    return redirect(destino)
