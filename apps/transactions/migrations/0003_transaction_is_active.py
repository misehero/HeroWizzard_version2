from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0002_add_idoklad_invoice"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="is_active",
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text="Inactive transactions are excluded from exports",
                verbose_name="Aktivní",
            ),
        ),
    ]
