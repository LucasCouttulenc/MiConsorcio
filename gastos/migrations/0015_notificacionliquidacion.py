import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0014_detallegastouf'),
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificacionLiquidacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creada', models.DateTimeField(auto_now_add=True)),
                ('leida_en', models.DateTimeField(blank=True, null=True)),
                ('detalle_liquidacion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones_propietario', to='gastos.detalleliquidacionuf')),
                ('propietario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones_liquidacion', to='usuarios.propietario')),
            ],
            options={
                'verbose_name': 'Notificación de liquidación',
                'verbose_name_plural': 'Notificaciones de liquidaciones',
                'ordering': ['-creada'],
                'unique_together': {('propietario', 'detalle_liquidacion')},
            },
        ),
    ]
