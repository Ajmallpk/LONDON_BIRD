# Generated by Django 5.2 on 2025-05-27 07:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checkout', '0006_alter_orderitem_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='product_discount_amount',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
    ]
