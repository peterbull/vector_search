# Generated by Django 3.2.6 on 2021-11-14 19:19

from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        VectorExtension();
    ]
