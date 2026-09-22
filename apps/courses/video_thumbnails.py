from pathlib import Path
import subprocess
import tempfile

from django.core.files import File

from .models import Lektion


VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}


def generate_lesson_video_thumbnail(lektion):
    if lektion.typ != Lektion.Typ.VIDEO or not lektion.datei:
        return False

    source_path = getattr(lektion.datei, "path", None)
    if not source_path or Path(source_path).suffix.lower() not in VIDEO_EXTENSIONS:
        return False

    source = Path(source_path)
    if not source.exists():
        return False

    thumbnail_name = f"{source.stem}-{lektion.pk}.jpg"
    with tempfile.TemporaryDirectory(prefix="lesson-thumb-") as tmpdir:
        output = Path(tmpdir) / "thumbnail.jpg"
        created = False
        for timestamp in ("3", "1", "0.1"):
            command = [
                "ffmpeg",
                "-y",
                "-ss",
                timestamp,
                "-i",
                str(source),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(output),
            ]
            try:
                result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            except OSError:
                return False
            if result.returncode == 0 and output.exists() and output.stat().st_size > 0:
                created = True
                break
        if not created:
            return False

        if lektion.video_thumbnail:
            lektion.video_thumbnail.delete(save=False)
        with output.open("rb") as handle:
            lektion.video_thumbnail.save(thumbnail_name, File(handle), save=False)
        lektion.save(update_fields=["video_thumbnail"])
    return True
