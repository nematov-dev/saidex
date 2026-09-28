# Avvalgi bitta-biznes rejimida BotConfig, ProjectSubscription va
# TelegramAccountConnection yozuvlari get_or_create(pk=1) bilan — ya'ni id'ni
# qo'lda berib — yaratilgan edi. Shuning uchun PostgreSQL'dagi id ketma-ketligi
# (sequence) hech qachon oshmagan va ikkinchi foydalanuvchi uchun yangi yozuv
# yaratishda "duplicate key (id)=(1)" xatosi chiqardi. Bu migratsiya
# ketma-ketliklarni jadvaldagi eng katta id'ga moslaydi.
from django.core.management.color import no_style
from django.db import migrations

MODELS = ["BotConfig", "ProjectSubscription", "TelegramAccountConnection"]


def reset_sequences(apps, schema_editor):
    connection = schema_editor.connection
    models = [apps.get_model("assistant", name) for name in MODELS]
    for sql in connection.ops.sequence_reset_sql(no_style(), models):
        schema_editor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0029_workspace_required"),
    ]

    operations = [
        migrations.RunPython(reset_sequences, migrations.RunPython.noop),
    ]
