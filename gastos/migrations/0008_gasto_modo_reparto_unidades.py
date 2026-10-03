from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('consorcios', '0008_unidadfuncional_alicuota_and_more'),
        ('gastos', '0007_gasto_comprobante'),
    ]

    operations = [
        migrations.AddField(
            model_name='gasto',
            name='modo_reparto',
            field=models.CharField(choices=[('general', 'General'), ('parcial', 'Parcial'), ('particular', 'Particular')], default='general', max_length=20, verbose_name='Modo de reparto'),
        ),
        migrations.AddField(
            model_name='gasto',
            name='unidades',
            field=models.ManyToManyField(blank=True, help_text='Particular: UF que pagan. Parcial: UF exentas.', related_name='gastos_afectados', to='consorcios.unidadfuncional', verbose_name='UF afectadas / exentas'),
        ),
        migrations.AlterField(
            model_name='gasto',
            name='grupo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='gastos', to='consorcios.grupoprorrateo', verbose_name='Columna / Grupo de Prorrateo'),
        ),
    ]
