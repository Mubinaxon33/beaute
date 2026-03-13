from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_usersecurityprofile_phone_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersecurityprofile",
            name="full_name",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
