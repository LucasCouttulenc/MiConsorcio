# gastos/views.py
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction

from consorcios.models import Consorcio, GrupoProrrateo
from .models import Gasto, Liquidacion
from .services import procesar_liquidacion_periodo
from django.utils.text import slugify

from django.http import HttpResponse
from .pdf import generar_pdf_liquidacion

CAMPOS_ADMIN = (
    'admin_razon', 'admin_nombre', 'admin_domicilio', 'admin_fiscal',
    'admin_cuit', 'admin_rpa', 'admin_telefono', 'admin_mail',
)

def _codigo_desde_nombre(nombre):
    return slugify(nombre).upper().replace('-', '')[:10] or 'GRUPO'


def generar_liquidacion(request):
    if request.method == 'POST':
        consorcio_id = request.POST.get('consorcio')
        mes = request.POST.get('mes')
        anio = request.POST.get('anio')
        periodo = f"{anio}-{mes}"
        fecha_vencimiento_1 = request.POST.get('fecha_vencimiento_1')
        fecha_cierre = request.POST.get('fecha_cierre')
        conceptos = request.POST.getlist('gastos_concepto[]')
        tipos = request.POST.getlist('gastos_tipo[]')
        subtipos = request.POST.getlist('gastos_subtipo[]')
        grupos_ids = request.POST.getlist('gastos_grupo[]')
        montos = request.POST.getlist('gastos_monto[]')

        if not consorcio_id or not conceptos:
            messages.error(request, "Debe seleccionar un consorcio y cargar al menos un gasto.")
            return redirect('generar_liquidacion')

        consorcio = get_object_or_404(Consorcio, id=consorcio_id)

        with transaction.atomic():
            Gasto.objects.filter(consorcio=consorcio, periodo=periodo).delete()

            for concepto, tipo, subtipo, grupo_val, monto in zip(conceptos, tipos, subtipos, grupos_ids, montos):
                grupo_str = str(grupo_val).strip() if grupo_val else ""

                if grupo_str.isdigit():
                    grupo = get_object_or_404(GrupoProrrateo, id=int(grupo_str), consorcio=consorcio)
                else:
                    if grupo_str.upper().startswith('NUEVO:'):
                        grupo_str = grupo_str.split(':', 1)[1].strip()

                    if grupo_str:
                        grupo, _ = GrupoProrrateo.objects.get_or_create(
                            consorcio=consorcio,
                            codigo=_codigo_desde_nombre(grupo_str),
                            defaults={'nombre': grupo_str},
                        )
                    else:
                        grupo = None

                monto_limpio = monto.replace(',', '.') if isinstance(monto, str) else monto

                Gasto.objects.create(
                    consorcio=consorcio,
                    concepto=concepto,
                    tipo=tipo,
                    subtipo=subtipo.strip().upper(), 
                    grupo=grupo,
                    monto=monto_limpio,
                    periodo=periodo,
                    fecha_comprobante=date.today(),
                    
                )

            liquidacion = procesar_liquidacion_periodo(
                consorcio=consorcio,
                periodo=periodo,
                fecha_vencimiento_1=fecha_vencimiento_1,
                fecha_cierre=fecha_cierre
            )
            liquidacion.datos_administracion = {c: request.POST.get(c, '').strip() for c in CAMPOS_ADMIN}
            liquidacion.save(update_fields=['datos_administracion'])
            
            messages.success(request, f"Liquidación correspondiente al período {periodo} generada exitosamente.")
            return redirect('detalle_liquidacion', liquidacion_id=liquidacion.id)

    consorcios = Consorcio.objects.prefetch_related('grupos_prorrateo').all()
    return render(request, 'generar_liquidacion.html', {'consorcios': consorcios})


def detalle_liquidacion(request, liquidacion_id):
    liquidacion = get_object_or_404(
        Liquidacion.objects.select_related('consorcio'),
        id=liquidacion_id,
    )
    detalles = (
        liquidacion.detalles_uf
        .select_related('unidad_funcional', 'unidad_funcional__propietario__usuario')
        .order_by('unidad_funcional__piso', 'unidad_funcional__departamento')
    )
    return render(request, 'detalle_liquidacion.html', {
        'liquidacion': liquidacion,
        'detalles': detalles,
    })



def descargar_liquidacion_pdf(request, liquidacion_id):
    liquidacion = get_object_or_404(
        Liquidacion.objects.select_related('consorcio'), id=liquidacion_id
    )
    gastos = (
        Gasto.objects
        .filter(consorcio=liquidacion.consorcio, periodo=liquidacion.periodo)
        .select_related('grupo')
        .order_by('grupo_id', 'id')
    )
    pdf = generar_pdf_liquidacion(liquidacion, gastos, liquidacion.datos_administracion)

    nombre = slugify(f"liquidacion-{liquidacion.consorcio.nombre}-{liquidacion.periodo}")
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nombre}.pdf"'
    return response