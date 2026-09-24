from django.core.management import call_command
from ..comando_base import ComandoBase
from django.contrib.auth import get_user_model
User = get_user_model()

class Command(ComandoBase):
    help = 'Ejecuta las migraciones de la base de datos.'

    def handle(self, *args, **options):
        if options[COMANDO_FLUSH]:
            self._flush_base()

        self._hacer_migraciones()

        self._correr_migraciones()

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