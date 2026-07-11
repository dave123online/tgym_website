from django.db import migrations


def backfill_profils(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Profil = apps.get_model("comptes", "Profil")
    for user in User.objects.all():
        if not Profil.objects.filter(user=user).exists():
            role = "staff" if (user.is_staff or user.is_superuser) else "adherent"
            Profil.objects.create(user=user, role=role)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("comptes", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_profils, noop),
    ]
