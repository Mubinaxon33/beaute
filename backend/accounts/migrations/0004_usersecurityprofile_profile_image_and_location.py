from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_usersecurityprofile_full_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersecurityprofile",
            name="location",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="usersecurityprofile",
            name="profile_image",
            field=models.ImageField(blank=True, null=True, upload_to="profile_images/%Y/%m/"),
        ),
    ]
