import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('consorcios', '0016_consorcio_fondo_reserva_nombre_and_more'),
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='unidadfuncional',
            name='propietario',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                to='usuarios.propietario',
            ),
        ),
    ]
