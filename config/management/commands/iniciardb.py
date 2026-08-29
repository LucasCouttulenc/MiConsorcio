from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from ..comando_base import ComandoBase
from pathlib import Path
from config.fixtures.administrador_de_fixtures import AdministradorDeFixtures
from config.comun import GRUPO_ADMINISTRADORES, GRUPO_PROPIETARIOS, PERMISOS_ADMINISTRADORES, PERMISOS_PROPIETARIOS
from django.contrib.auth import get_user_model
User = get_user_model()

ARCHIVO_DE_FIXTURES = 'fixtures.json'
CARPETA_MODELOS = 'modelos'

class Command(ComandoBase):
    help = 'Inicializa la base de datos: limpia, migra, crea grupos y permisos, y crea un superusuario.'

    def handle(self, *args, **options):

        self._flush_base()

        self._hacer_migraciones()

        self._correr_migraciones()

        self._generar_fixtures()

        self._cargar_fixtures()

        self._eliminar_fixtures()

        self._cargar_permisos()

    def _flush_base(self):
        def flush_base():
            call_command('flush', '--noinput')

        self._correr_tarea(
            flush_base,
            "Limpiando la base de datos...",
            "Error al limpiar la base de datos.",
            "Base de datos limpiada correctamente."
        )

    def _hacer_migraciones(self):
        def hacer_migraciones():
            call_command('makemigrations')

        self._correr_tarea(
            hacer_migraciones,
            "Creando migraciones...",
            "Error al crear migraciones.",
            "Migraciones creadas correctamente."
        )
    
    def _correr_migraciones(self):
        def correr_migraciones():
            call_command('migrate')

        self._correr_tarea(
            correr_migraciones,
            "Ejecutando migraciones...",
            "Error al ejecutar migraciones.",
            "Migraciones ejecutadas correctamente."
        )

    def _generar_fixtures(self):
        def generar_fixtures():
            AdministradorDeFixtures(carpeta=CARPETA_MODELOS).exportar_a_archivo(ARCHIVO_DE_FIXTURES)
            
        self._correr_tarea(
            generar_fixtures,
            "Generando fixtures...",
            "Error al generar fixtures",
            "Fixtures generadas correctamente"
        )

    def _cargar_fixtures(self):
        def cargar_fixtures():
            call_command('loaddata', ARCHIVO_DE_FIXTURES)

        self._correr_tarea(
            cargar_fixtures,
            "Cargando fixtures en la base...",
            "Error al cargar fixtures en la base",
            "Fixtures cargados correctamente"
        )

    def _cargar_permisos(self):
        def cargar_permisos():
            grupo_administradores, _ = Group.objects.get_or_create(name=GRUPO_ADMINISTRADORES)
            grupo_propietarios, _ = Group.objects.get_or_create(name=GRUPO_PROPIETARIOS)
            
            grupos_y_permisos = [
                (grupo_administradores, PERMISOS_ADMINISTRADORES),
                (grupo_propietarios, PERMISOS_PROPIETARIOS),
            ]

            for grupo, permisos in grupos_y_permisos:
                for p in permisos:
                    grupo.permissions.add(Permission.objects.get(codename=p))

        self._correr_tarea(
            cargar_permisos,
            "Cargando permisos...",
            "Error al cargar permisos.",
            "Permisos cargados correctamente."
        )

    def _eliminar_fixtures(self):
        def eliminar_fixtures():
            Path(ARCHIVO_DE_FIXTURES).unlink()

        self._correr_tarea(
            eliminar_fixtures,
            "Eliminando archivo de fixtures...",
            "Error al eliminar archivo de fixtures",
            "Archivo de fixtures eliminado correctamente"
        ) 