from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0003_transaction_is_active"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="is_deleted",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Soft-deleted transactions are excluded from all views",
                verbose_name="Smazáno",
            ),
        ),
    ]
