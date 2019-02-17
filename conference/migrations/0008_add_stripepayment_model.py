# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-02-17 15:54
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("assopy", "0010_add_uuid_to_Order"),
        ("conference", "0007_remove_special_place"),
    ]

    operations = [
        migrations.CreateModel(
            name="StripePayment",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("token", models.CharField(max_length=100)),
                ("uuid", models.CharField(max_length=40)),
                ("token_type", models.CharField(max_length=20)),
                ("description", models.CharField(max_length=255)),
                ("email", models.CharField(max_length=255)),
                (
                    "amount",
                    models.DecimalField(decimal_places=2, max_digits=10),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("NEW", "New"),
                            ("SUCCESSFUL", "Successful"),
                            ("FAILED", "Failed"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "message",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="assopy.Order",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        )
    ]
