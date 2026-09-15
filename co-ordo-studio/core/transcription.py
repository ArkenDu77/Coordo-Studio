from __future__ import annotations
import os
import tempfile
from typing import BinaryIO
from .models import TranscriptSegment


def demo_transcript() -> list[TranscriptSegment]:
    return [
        TranscriptSegment("t1", 12, 33, "On reprend la définition de la mémoire de travail. C'est la même idée que l'an dernier, je la formule juste autrement.", "contenu"),
        TranscriptSegment("t2", 55, 84, "Point important : la boucle phonologique comprend désormais dans votre cours le stockage phonologique et le processus de répétition articulatoire.", "important"),
        TranscriptSegment("t3", 122, 151, "Je vous raconte juste une anecdote de mon stage, ça ne sera évidemment pas demandé à l'examen.", "digression"),
        TranscriptSegment("t4", 181, 215, "Pour l'examen, retenez surtout que l'administrateur central coordonne les systèmes esclaves et intervient dans le partage attentionnel.", "important"),
        TranscriptSegment("t5", 274, 302, "L'exemple du numéro de téléphone qu'on répète mentalement peut vous aider, mais ce n'est pas à apprendre en tant que tel.", "exemple"),
        TranscriptSegment("t6", 355, 388, "La partie historique sur le modèle de 1974, je ne la détaille plus cette année. Gardez néanmoins la logique générale du modèle.", "incertain"),
    ]


def transcribe_audio(uploaded_file) -> list[TranscriptSegment]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY absente")
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")

    suffix = ".mp3"
    name = getattr(uploaded_file, "name", "audio.mp3")
    if "." in name:
        suffix = "." + name.rsplit(".", 1)[-1]
    data = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(data); tmp.flush()
        with open(tmp.name, "rb") as f:
            # whisper-1 is used by default because it reliably exposes segment timestamps.
            tr = client.audio.transcriptions.create(
                model=model,
                file=f,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
                language="fr",
            )
    segs = getattr(tr, "segments", None) or []
    result = []
    for i, s in enumerate(segs):
        if hasattr(s, "model_dump"):
            d = s.model_dump()
        elif isinstance(s, dict):
            d = s
        else:
            d = s.__dict__
        result.append(TranscriptSegment(
            id=f"t{i+1}", start=float(d.get("start", 0)), end=float(d.get("end", 0)), text=str(d.get("text", "")).strip()
        ))
    if not result:
        text = getattr(tr, "text", str(tr))
        result = [TranscriptSegment("t1", 0, 0, text)]
    return result
