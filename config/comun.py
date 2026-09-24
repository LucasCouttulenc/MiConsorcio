FILAS_POR_PAGINA = 9

#####################################################################
#                              GRUPOS                               #
#####################################################################

GRUPO_ADMINISTRADORES = "Administradores"
GRUPO_PROPIETARIOS = "Propietarios"

#####################################################################
#                            PERMISOS                               #
#####################################################################

PERMISOS_ADMINISTRADORES = [
    "add_consorcio",
    "view_consorcio",
    "change_consorcio",
    "add_unidadfuncional",
    "view_unidadfuncional",
    "change_unidadfuncional",
]

PERMISOS_PROPIETARIOS = [
    "view_consorcio",
    # TODO: agregar solo permisos de lectura supongo
]