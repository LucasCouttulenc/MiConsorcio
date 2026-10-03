from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0006_detalleliquidacionuf_alicuota'),
    ]

    operations = [
        migrations.AddField(
            model_name='gasto',
            name='comprobante',
            field=models.FileField(blank=True, null=True, upload_to='comprobantes/%Y/%m/', verbose_name='Comprobante / Factura'),
        ),
    ]
