"""
Data migration to set initial sort_order values (10, 20, 30...)
so items have meaningful ordering out of the box.
"""

from django.db import migrations


def set_sort_order(apps, schema_editor):
    Project = apps.get_model("transactions", "Project")
    Product = apps.get_model("transactions", "Product")
    ProductSubgroup = apps.get_model("transactions", "ProductSubgroup")

    for Model in [Project, Product]:
        for i, obj in enumerate(Model.objects.order_by("name")):
            Model.objects.filter(pk=obj.pk).update(sort_order=(i + 1) * 10)

    for i, obj in enumerate(ProductSubgroup.objects.order_by("product__name", "name")):
        ProductSubgroup.objects.filter(pk=obj.pk).update(sort_order=(i + 1) * 10)


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0006_add_sort_order_to_lookups"),
    ]

    operations = [
        migrations.RunPython(set_sort_order, migrations.RunPython.noop),
    ]
