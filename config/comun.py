FILAS_POR_PAGINA = 8
#####################################################################
#                              GRUPOS                               #
#####################################################################

GRUPO_ADMINISTRADORES = "Administradores"
GRUPO_PROPIETARIOS = "Propietarios"

#####################################################################
#                            PERMISOS                               #
#####################################################################

# Prefijos de apps para no repetir el "app_label" en cada permiso
APPS_ADMINISTRADOR = ["consorcios", "gastos"]

PERMISOS_ADMINISTRADORES = [
    # Consorcios
    "add_consorcio",
    "view_consorcio",
    "change_consorcio",
    "delete_consorcio",

    # Unidades funcionales
    "add_unidadfuncional",
    "view_unidadfuncional",
    "change_unidadfuncional",
    "delete_unidadfuncional",

    # Personal
    "add_personal",
    "view_personal",
    "change_personal",
    "delete_personal",

    # Grupos de prorrateo
    "add_grupoprorrateo",
    "view_grupoprorrateo",
    "change_grupoprorrateo",
    "delete_grupoprorrateo",

    # Coeficientes UF  
    "add_coeficienteuf",
    "view_coeficienteuf",
    "change_coeficienteuf",
    "delete_coeficienteuf",

    # Liquidaciones / gastos
    "add_liquidacion",
    "view_liquidacion",
    "change_liquidacion",
    "delete_liquidacion",
    "add_gasto",
    "view_gasto",
    "change_gasto",
    "delete_gasto",
    "view_detalleliquidacionuf",
    
    
    
    # Rubros  
    "add_rubro",
    "view_rubro",
    "change_rubro",
    "delete_rubro",
]

PERMISOS_PROPIETARIOS = [
    "view_consorcio",
    "view_unidadfuncional",
    "view_liquidacion",
    "view_gasto",
    "view_detalleliquidacionuf",
]