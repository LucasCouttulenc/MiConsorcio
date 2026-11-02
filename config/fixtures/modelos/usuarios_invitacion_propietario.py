import hashlib
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from ..fixture import Fixture
from consorcios.models import Consorcio, UnidadFuncional
from usuarios.models import InvitacionPropietario, Propietario

User = get_user_model()
DIAS_DE_VIGENCIA = 7


def token_de_prueba(unidad_funcional):
    """
    Token fijo y conocido, para poder probar el link de invitación a mano.
    En la base solo se guarda su hash (sha256 en hexadecimal, 64 caracteres).
    """
    return f'invitacion-prueba-{unidad_funcional}'


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class FixtureDeInvitacionPropietario(Fixture):
    """
    Por consorcio:
      - La UF sin propietario: invitación vigente, vencida o ninguna (rotando por consorcio).
      - Una UF con propietario: invitación ya aceptada por él.
    """

    dependencias_extra = (Propietario, User)

    def __init__(self):
        super().__init__(InvitacionPropietario)

    def campos(self):
        adm = self.administrador
        ahora = (timezone.localtime() if settings.USE_TZ else timezone.now()).replace(microsecond=0)
        resultado = []

        def invitacion(uf, email, dias_desde_creada, enviada=True, aceptada_a_los_dias=None):
            creada = ahora - timedelta(days=dias_desde_creada)
            resultado.append({
                'unidad_funcional': uf,
                'email': email,
                'token_hash': _hash(token_de_prueba(uf)),
                'creada': creada.isoformat(),
                'expira': (creada + timedelta(days=DIAS_DE_VIGENCIA)).isoformat(),
                'enviada': (creada + timedelta(minutes=1)).isoformat() if enviada else None,
                'aceptada': (creada + timedelta(days=aceptada_a_los_dias)).isoformat()
                            if aceptada_a_los_dias is not None else None,
            })

        for indice, consorcio in enumerate(adm.obtener_ids(Consorcio)):
            ufs = adm.obtener_ids(UnidadFuncional, consorcio=consorcio)

            for uf in ufs:
                if adm.obtener_valor(UnidadFuncional, uf, 'propietario') is not None:
                    continue
                email = f'nuevo.propietario.uf{uf}@example.com'
                if indice % 3 == 0:
                    invitacion(uf, email, dias_desde_creada=2)                       # vigente
                elif indice % 3 == 1:
                    invitacion(uf, email, dias_desde_creada=20)                      # vencida
                # indice % 3 == 2: todavía no se invitó a nadie

            # Un propietario que llegó por invitación (la quinta UF, que no tiene rol en gastos).
            if len(ufs) > 4:
                propietario = adm.obtener_valor(UnidadFuncional, ufs[4], 'propietario')
                if propietario is not None:
                    usuario = adm.obtener_valor(Propietario, propietario, 'usuario')
                    invitacion(ufs[4], adm.obtener_valor(User, usuario, 'email'),
                               dias_desde_creada=60, aceptada_a_los_dias=1)

        return resultado