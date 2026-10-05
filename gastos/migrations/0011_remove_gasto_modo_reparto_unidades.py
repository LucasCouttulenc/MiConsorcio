from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0010_pago_notas_admin'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gasto',
            name='modo_reparto',
        ),
        migrations.RemoveField(
            model_name='gasto',
            name='unidades',
        ),
    ]
