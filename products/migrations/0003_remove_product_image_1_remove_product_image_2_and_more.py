# Generated by Django 5.2 on 2025-04-29 14:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_variant'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='image_1',
        ),
        migrations.RemoveField(
            model_name='product',
            name='image_2',
        ),
        migrations.RemoveField(
            model_name='product',
            name='image_3',
        ),
        migrations.RemoveField(
            model_name='product',
            name='image_main',
        ),
        migrations.RemoveField(
            model_name='product',
            name='price',
        ),
        migrations.AddField(
            model_name='variant',
            name='price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
    ]
