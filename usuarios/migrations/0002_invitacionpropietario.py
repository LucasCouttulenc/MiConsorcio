import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('consorcios', '0017_alter_unidadfuncional_propietario_nullable'),
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvitacionPropietario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('token_hash', models.CharField(max_length=64, unique=True)),
                ('creada', models.DateTimeField(auto_now_add=True)),
                ('expira', models.DateTimeField()),
                ('enviada', models.DateTimeField(blank=True, null=True)),
                ('aceptada', models.DateTimeField(blank=True, null=True)),
                ('unidad_funcional', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='invitacion_propietario', to='consorcios.unidadfuncional',
                )),
            ],
            options={
                'verbose_name': 'Invitación de propietario',
                'verbose_name_plural': 'Invitaciones de propietarios',
            },
        ),
    ]
