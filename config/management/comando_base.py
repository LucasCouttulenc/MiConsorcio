from django.core.management.base import BaseCommand
from colorama import init, Fore, Style

init(autoreset=True)

class ComandoBase(BaseCommand):

    def _correr_tarea(self, func, paso, error, exito):
        try:
            self._paso(paso)
            resultado = func()
            self._exito(exito)
            return resultado
        except Exception as e:
            self._error(f"{error}: {e}")
            raise e

    def _exito(self, message):
        print(f"{Fore.GREEN}✅ {message} {Style.RESET_ALL}\n")

    def _notificacion(self, message):
        print(f"{Fore.YELLOW}🔔 {message} {Style.RESET_ALL}\n")

    def _error(self, message):
        print(f"{Fore.RED}❌ {message} {Style.RESET_ALL}\n")

    def _paso(self, message):
        print(f"{Fore.CYAN}🚀 {message} {Style.RESET_ALL}")