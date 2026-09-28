# gastos/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from consorcios.models import Consorcio, GrupoProrrateo
from .models import Gasto, Liquidacion
from .services import procesar_liquidacion_periodo
from datetime import date

def generar_liquidacion(request):
    if request.method == 'POST':
        consorcio_id = request.POST.get('consorcio')
        mes = request.POST.get('mes')
        anio = request.POST.get('anio')
        periodo = f"{anio}-{mes}"
        fecha_cierre = request.POST.get('fecha_cierre')
        fecha_vencimiento_1 = request.POST.get('fecha_vencimiento_1')

        conceptos = request.POST.getlist('gastos_concepto[]')
        tipos = request.POST.getlist('gastos_tipo[]')
        grupos_ids = request.POST.getlist('gastos_grupo[]')
        montos = request.POST.getlist('gastos_monto[]')

        if not consorcio_id or not conceptos:
            messages.error(request, "Debe seleccionar un consorcio y cargar al menos un gasto.")
            return redirect('generar_liquidacion')

        consorcio = get_object_or_404(Consorcio, id=consorcio_id)

        with transaction.atomic():
            Gasto.objects.filter(consorcio=consorcio, periodo=periodo).delete()

            for concepto, tipo, grupo_val, monto in zip(conceptos, tipos, grupos_ids, montos):
                if grupo_val.startswith('NUEVO:'):
                    nombre_columna = grupo_val.replace('NUEVO:', '', 1)
                    grupo, _ = GrupoProrrateo.objects.get_or_create(
                        consorcio=consorcio,
                        nombre=nombre_columna
                    )
                else:
                    grupo = get_object_or_404(GrupoProrrateo, id=int(grupo_val))

                Gasto.objects.create(
                    consorcio=consorcio,
                    concepto=concepto,
                    tipo=tipo,
                    grupo=grupo,
                    monto=monto,
                    periodo=periodo,
                    fecha_comprobante=date.today()
                )

            liquidacion = procesar_liquidacion_periodo(
                consorcio=consorcio,
                periodo=periodo,
                fecha_vencimiento_1=fecha_vencimiento_1,
                fecha_cierre=fecha_cierre
            )
            messages.success(request, f"Liquidación correspondiente al período {periodo} generada exitosamente.")
            return redirect('detalle_liquidacion', liquidacion_id=liquidacion.id)

    # Se utiliza solo prefetch_related para los grupos de prorrateo
    consorcios = Consorcio.objects.prefetch_related('grupos_prorrateo').all()
    return render(request, 'generar_liquidacion.html', {'consorcios': consorcios})