from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0008_gasto_modo_reparto_unidades'),
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
