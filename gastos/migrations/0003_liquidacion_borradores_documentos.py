import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('gastos', '0002_alter_gasto_concepto_alter_gasto_grupo_and_more')]

    operations = [
        migrations.AddField(model_name='liquidacion', name='fecha_cierre', field=models.DateField(blank=True, null=True, verbose_name='Cierre de expensas')),
        migrations.AlterField(model_name='liquidacion', name='fecha_vencimiento_1', field=models.DateField(blank=True, null=True, verbose_name='Primer Vencimiento')),
        migrations.AddField(model_name='liquidacion', name='datos_borrador', field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name='liquidacion', name='documento', field=models.BinaryField(blank=True, null=True)),
        migrations.AddField(model_name='liquidacion', name='actualizada', field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name='gasto', name='liquidacion', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='gastos_cargados', to='gastos.liquidacion')),
        migrations.AddField(model_name='gasto', name='subtipo', field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='gasto', name='posicion', field=models.PositiveIntegerField(default=0)),
    ]
