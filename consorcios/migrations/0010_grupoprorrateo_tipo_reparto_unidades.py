from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('consorcios', '0009_personal'),
    ]

    operations = [
        migrations.AddField(
            model_name='grupoprorrateo',
            name='tipo_reparto',
            field=models.CharField(choices=[('general', 'General'), ('parcial', 'Parcial'), ('particular', 'Particular')], default='general', max_length=20, verbose_name='Tipo de reparto'),
        ),
        migrations.AddField(
            model_name='grupoprorrateo',
            name='unidades',
            field=models.ManyToManyField(blank=True, help_text='Particular: UF que pagan. Parcial: UF exentas. General: se ignora.', related_name='columnas', to='consorcios.unidadfuncional', verbose_name='UF afectadas / exentas'),
        ),
    ]
