# Generated by Django 5.2 on 2025-05-19 12:43

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BlogPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('slug', models.SlugField(blank=True, help_text='URL-friendly version of the title (auto-generated).', max_length=250, unique=True)),
                ('content', models.TextField(help_text='The main content of the blog post (can use Markdown or HTML).')),
                ('published_date', models.DateTimeField(default=django.utils.timezone.now, help_text='The date and time the post was published.')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('published', 'Published')], default='published', max_length=10)),
            ],
            options={
                'ordering': ['-published_date'],
            },
        ),
    ]
