# Generated by Django 5.2 on 2025-06-02 04:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('checkout', '0010_order_shipping'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='tax',
        ),
    ]
