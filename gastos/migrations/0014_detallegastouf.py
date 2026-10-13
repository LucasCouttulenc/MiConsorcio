import django.db.models.deletion
from decimal import Decimal, ROUND_HALF_UP
from django.db import migrations, models


def crear_distribuciones_existentes(apps, schema_editor):
    Gasto = apps.get_model('gastos', 'Gasto')
    Liquidacion = apps.get_model('gastos', 'Liquidacion')
    UnidadFuncional = apps.get_model('consorcios', 'UnidadFuncional')
    Distribucion = apps.get_model('gastos', 'DetalleGastoUF')
    redondear = lambda valor: Decimal(valor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    for liquidacion in Liquidacion.objects.filter(cerrada=True).iterator():
        unidades = list(UnidadFuncional.objects.filter(consorcio_id=liquidacion.consorcio_id))
        for gasto in Gasto.objects.filter(liquidacion_id=liquidacion.pk).select_related('grupo'):
            grupo = gasto.grupo
            tipo = grupo.tipo_reparto if grupo else 'general'
            seleccion = set(grupo.unidades.values_list('pk', flat=True)) if grupo else set()
            if tipo == 'particular':
                pagadores = [uf for uf in unidades if uf.pk in seleccion]
            elif tipo == 'parcial':
                pagadores = [uf for uf in unidades if uf.pk not in seleccion]
            else:
                pagadores = unidades
            pagadores = pagadores or unidades
            if not pagadores:
                continue
            pesos = [uf.alicuota for uf in pagadores]
            total_pesos = sum(pesos)
            if total_pesos <= 0:
                pesos = [Decimal('1')] * len(pagadores)
                total_pesos = Decimal(len(pagadores))
            asignado = Decimal('0.00')
            for indice, (uf, peso) in enumerate(zip(pagadores, pesos)):
                parte = redondear(gasto.monto * peso / total_pesos) if indice < len(pagadores) - 1 else gasto.monto - asignado
                asignado += parte
                porcentaje = (parte * Decimal('100') / gasto.monto).quantize(Decimal('0.0001')) if gasto.monto else Decimal('0')
                Distribucion.objects.create(
                    gasto_id=gasto.pk, unidad_funcional_id=uf.pk,
                    porcentaje_aplicado=porcentaje, monto_asignado=parte,
                )


class Migration(migrations.Migration):

    dependencies = [
        ('consorcios', '0014_alter_personal_cargo'),
        ('gastos', '0013_serviciorecurrente'),
    ]

    operations = [
        migrations.CreateModel(
            name='DetalleGastoUF',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('porcentaje_aplicado', models.DecimalField(decimal_places=4, default=0, max_digits=7)),
                ('monto_asignado', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('gasto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='distribuciones_uf', to='gastos.gasto')),
                ('unidad_funcional', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='distribuciones_gastos', to='consorcios.unidadfuncional')),
            ],
            options={
                'verbose_name': 'Distribución de gasto por UF',
                'verbose_name_plural': 'Distribuciones de gastos por UF',
                'unique_together': {('gasto', 'unidad_funcional')},
            },
        ),
        migrations.RunPython(crear_distribuciones_existentes, migrations.RunPython.noop),
    ]
