from __future__ import annotations
import json
import os
import re
import uuid
from .models import DocumentBlock, TranscriptSegment, Suggestion

SYSTEM = r'''
Tu es l'éditeur pédagogique de Co-Ordo Studio. Tu actualises une fiche d'examen à partir d'un cours audio.
Règles absolues :
1. Le document précédent est le socle. Ne reformule jamais une notion existante juste parce que le professeur la formule différemment.
2. Ajoute seulement les nouveautés réellement utiles à l'examen. Ignore anecdotes, répétitions, digressions et bavardage.
3. Un nouvel exemple est en général ignoré ; en SSS, tu peux le garder s'il aide réellement une réponse ouverte ou la compréhension.
4. Une notion non citée cette année n'est PAS automatiquement supprimée. Les éléments structurants, utiles à la compréhension ou potentiellement vus en TD restent.
5. Une étoile ★ est un signal fort d'importance/annales et protège fortement de la suppression.
6. Une suppression doit être étayée. Si tu hésites, action=review.
7. Chaque ajout doit être soutenu par un passage précis de la transcription. N'invente rien.
8. Objectif : fiche concise pour réussir l'examen, pas transcription exhaustive.
9. Pour une reformulation sans changement de fond : no_change.
10. Les actions réellement appliquables sont insert_after, insert_before, strike_text, replace_text, no_change, review.
Réponds en JSON strict, sans markdown, avec la forme {"suggestions":[...]}. Chaque suggestion contient : action, block_id, anchor_text, new_text, reason, confidence (0..1), evidence, timestamp_start, timestamp_end, category, auto_safe.
'''


def demo_suggestions(blocks: list[DocumentBlock]) -> list[Suggestion]:
    ids = [b.id for b in blocks] or ["p-0"]
    texts = [b.text for b in blocks] or ["Définition de la mémoire de travail"]
    def bid(i): return ids[min(i, len(ids)-1)]
    def btxt(i): return texts[min(i, len(texts)-1)]
    return [
        Suggestion("s1", "insert_after", bid(0), btxt(0), "La boucle phonologique comporte un stockage phonologique et un processus de répétition articulatoire.", "Nouveauté explicitement présentée comme importante dans le cours.", .96, "Point important : la boucle phonologique comprend…", 55, 84, "ajout", True),
        Suggestion("s2", "no_change", bid(0), btxt(0), "", "Le professeur reformule la définition sans changement de fond.", .98, "C'est la même idée que l'an dernier…", 12, 33, "inchangé", True),
        Suggestion("s3", "insert_after", bid(1), btxt(1), "L'administrateur central intervient notamment dans le partage attentionnel.", "Consigne explicite pour l'examen.", .94, "Pour l'examen, retenez surtout…", 181, 215, "ajout", True),
        Suggestion("s4", "review", bid(2), btxt(2), "", "Le professeur ne détaille plus cette partie mais demande de conserver la logique générale : suppression ambiguë.", .61, "La partie historique… je ne la détaille plus… Gardez néanmoins…", 355, 388, "à vérifier", False),
    ]


def _json_from_text(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if not m: raise
        return json.loads(m.group(0))


def analyze(blocks: list[DocumentBlock], transcript: list[TranscriptSegment], licence: str) -> list[Suggestion]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return demo_suggestions(blocks)
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_ANALYSIS_MODEL", "gpt-5.6-terra")
    payload = {
        "licence": licence,
        "document_blocks": [b.__dict__ for b in blocks],
        "transcript_segments": [s.__dict__ for s in transcript],
    }
    prompt = SYSTEM + "\nDONNEES:\n" + json.dumps(payload, ensure_ascii=False)
    resp = client.responses.create(model=model, input=prompt)
    data = _json_from_text(resp.output_text)
    out = []
    valid_ids = {b.id for b in blocks}
    for raw in data.get("suggestions", []):
        block_id = raw.get("block_id")
        if block_id not in valid_ids:
            continue
        action = raw.get("action", "review")
        conf = max(0.0, min(1.0, float(raw.get("confidence", 0.5))))
        # Safety: automatic deletion/replacement requires high confidence; otherwise force review.
        if action in {"strike_text", "replace_text"} and conf < 0.9:
            action = "review"
            raw["auto_safe"] = False
        out.append(Suggestion(
            id=str(raw.get("id") or uuid.uuid4()),
            action=action,
            block_id=block_id,
            anchor_text=str(raw.get("anchor_text") or ""),
            new_text=str(raw.get("new_text") or ""),
            reason=str(raw.get("reason") or ""),
            confidence=conf,
            evidence=str(raw.get("evidence") or ""),
            timestamp_start=raw.get("timestamp_start"),
            timestamp_end=raw.get("timestamp_end"),
            category=str(raw.get("category") or "modification"),
            auto_safe=bool(raw.get("auto_safe", False)),
        ))
    return out
