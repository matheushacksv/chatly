from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0007_whatsappinstance_evogo_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='whatsappinstance',
            name='needs_qr',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='whatsappinstance',
            name='reconnect_attempts',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='whatsappinstance',
            name='last_seen_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
