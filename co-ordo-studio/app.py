from __future__ import annotations
import os
import time
from dataclasses import replace
from dotenv import load_dotenv
import streamlit as st

from core.docx_xml import extract_blocks, apply_suggestions
from core.transcription import transcribe_audio, demo_transcript
from core.analysis import analyze, demo_suggestions
from core.demo import demo_blocks

load_dotenv()
st.set_page_config(page_title="Co-Ordo Studio", page_icon="✦", layout="wide", initial_sidebar_state="collapsed")

st.markdown(r"""
<style>
:root{--ink:#111827;--muted:#667085;--line:#e5e7eb;--panel:#ffffff;--bg:#f7f8fa;--blue:#d9f2ff;--accent:#111827}
.stApp{background:var(--bg);color:var(--ink)}
.block-container{max-width:1800px;padding-top:1.2rem;padding-bottom:2rem}
h1,h2,h3{letter-spacing:-.025em}.small{font-size:.82rem;color:var(--muted)}
.hero{display:flex;justify-content:space-between;align-items:center;padding:.8rem 0 1.2rem;border-bottom:1px solid var(--line);margin-bottom:1rem}
.brand{font-size:1.35rem;font-weight:800}.brand span{font-weight:500;color:var(--muted)}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px;box-shadow:0 1px 2px rgba(16,24,40,.03)}
.stat{background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px 12px}.stat b{font-size:1.15rem}
.tx{padding:9px 10px;border-bottom:1px solid #f0f1f3;line-height:1.45}.ts{font-size:.75rem;color:#475467;font-variant-numeric:tabular-nums}
.added{background:#d9f2ff;padding:2px 3px;border-radius:3px;font-weight:700}.removed{background:#d9f2ff;padding:2px 3px;border-radius:3px;text-decoration:line-through}.star{font-weight:750}
.sugg{border:1px solid var(--line);border-left:4px solid #98a2b3;border-radius:10px;padding:10px 12px;margin:8px 0;background:#fff}.sugg-add{border-left-color:#0ea5e9}.sugg-del{border-left-color:#f97316}.sugg-review{border-left-color:#eab308}
.conf{font-size:.76rem;color:#667085}.pill{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:2px 7px;font-size:.72rem;margin-right:5px}
section[data-testid="stFileUploader"]{background:#fff;border:1px dashed #cbd5e1;border-radius:14px;padding:8px}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:14px}
</style>
""", unsafe_allow_html=True)


def fmt_time(seconds):
    if seconds is None: return "—"
    seconds = int(seconds)
    return f"{seconds//60:02d}:{seconds%60:02d}"

if "mode" not in st.session_state: st.session_state.mode = "import"
if "blocks" not in st.session_state: st.session_state.blocks = None
if "transcript" not in st.session_state: st.session_state.transcript = None
if "suggestions" not in st.session_state: st.session_state.suggestions = None
if "docx_bytes" not in st.session_state: st.session_state.docx_bytes = None
if "licence" not in st.session_state: st.session_state.licence = "Psychologie"

st.markdown('<div class="hero"><div class="brand">✦ Co-Ordo Studio <span>/ actualisation éditoriale</span></div><div class="small">DOCX maître · preuves audio · validation humaine</div></div>', unsafe_allow_html=True)

if st.session_state.mode == "import":
    c1,c2 = st.columns([1.15,.85], gap="large")
    with c1:
        st.subheader("Nouvelle actualisation")
        st.caption("Dépose le cours actuel et la fiche de l’année précédente. Le document Word reste la source maître.")
        audio = st.file_uploader("Cours audio · MP3", type=["mp3","m4a","wav","mp4"])
        docx = st.file_uploader("Fiche N-1 · Word", type=["docx"])
        licence = st.segmented_control("Licence", ["Psychologie","SSS"], default="Psychologie") or "Psychologie"
        matiere = st.text_input("Matière / chapitre (facultatif)", placeholder="Ex. Psychologie cognitive — Mémoire")
        api_ok = bool(os.getenv("OPENAI_API_KEY"))
        if not api_ok:
            st.info("Mode démo actif : aucune clé OPENAI_API_KEY détectée. Tu peux tester tout le workflow immédiatement.")
        a,b = st.columns(2)
        with a:
            use_demo = st.button("Ouvrir le projet démo", use_container_width=True, type="secondary")
        with b:
            launch = st.button("Lancer l’actualisation", use_container_width=True, type="primary", disabled=not (audio and docx))

        if use_demo:
            st.session_state.blocks = demo_blocks()
            st.session_state.transcript = demo_transcript()
            st.session_state.suggestions = demo_suggestions(st.session_state.blocks)
            st.session_state.docx_bytes = None
            st.session_state.licence = licence
            st.session_state.mode = "workspace"
            st.rerun()

        if launch:
            progress = st.progress(0, text="Extraction du document Word…")
            try:
                blocks, docx_bytes = extract_blocks(docx)
                progress.progress(22, text="Transcription audio…")
                transcript = transcribe_audio(audio) if api_ok else demo_transcript()
                progress.progress(63, text="Analyse pédagogique et comparaison…")
                suggestions = analyze(blocks, transcript, licence)
                progress.progress(100, text="Prêt à relire")
                st.session_state.blocks = blocks
                st.session_state.transcript = transcript
                st.session_state.suggestions = suggestions
                st.session_state.docx_bytes = docx_bytes
                st.session_state.licence = licence
                st.session_state.mode = "workspace"
                time.sleep(.2); st.rerun()
            except Exception as e:
                st.error(f"Impossible de terminer l’analyse : {e}")
    with c2:
        st.subheader("Règles de sécurité")
        st.markdown("""
        <div class="card">
        <b>Le Word n'est jamais réécrit globalement.</b><br><br>
        • Reformulation → aucun changement<br>
        • Ajout utile examen → <span class="added">gras + bleu</span><br>
        • Suppression certaine → <span class="removed">barré + bleu</span><br>
        • ★ protège une notion importante<br>
        • Incertitude → <b>À vérifier</b><br>
        • Chaque ajout doit citer l'audio
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        st.markdown('<div class="card"><b>But</b><br><span class="small">Une fiche concise et fidèle à l’examen, pas une transcription du professeur. Les anecdotes, répétitions et digressions sont filtrées.</span></div>', unsafe_allow_html=True)

else:
    blocks = st.session_state.blocks or []
    transcript = st.session_state.transcript or []
    suggestions = st.session_state.suggestions or []

    top1,top2,top3,top4,top5,top6 = st.columns([1,1,1,1,1,1.2])
    adds = sum(s.action in ("insert_after","insert_before","replace_text") for s in suggestions)
    dels = sum(s.action == "strike_text" for s in suggestions)
    revs = sum(s.action == "review" for s in suggestions)
    stars = sum(b.starred for b in blocks)
    with top1: st.metric("Ajouts", adds)
    with top2: st.metric("Suppressions", dels)
    with top3: st.metric("À vérifier", revs)
    with top4: st.metric("Notions ★", stars)
    with top5: st.metric("Segments audio", len(transcript))
    with top6:
        if st.button("← Nouvelle actualisation", use_container_width=True):
            st.session_state.mode="import"; st.rerun()

    st.divider()
    left, center, right = st.columns([1.02,1.28,1.08], gap="medium")

    with left:
        st.markdown("### Transcription")
        q = st.text_input("Rechercher", placeholder="Mot ou notion…", label_visibility="collapsed")
        cats = st.multiselect("Filtrer", ["important","contenu","exemple","digression","incertain"], placeholder="Tous les segments")
        for seg in transcript:
            if q and q.lower() not in seg.text.lower(): continue
            if cats and seg.category not in cats: continue
            badge = {"important":"Important","digression":"Digression","exemple":"Exemple","incertain":"Incertain"}.get(seg.category, "Cours")
            st.markdown(f'<div class="tx"><span class="ts">{fmt_time(seg.start)}–{fmt_time(seg.end)}</span> <span class="pill">{badge}</span><br>{seg.text}</div>', unsafe_allow_html=True)

    with center:
        st.markdown("### Fiche actualisée")
        st.caption("Aperçu de relecture. Le fichier exporté est patché à partir du DOCX original.")
        by_block = {}
        for s in suggestions:
            by_block.setdefault(s.block_id, []).append(s)
        for b in blocks:
            star_cls = "star" if b.starred else ""
            st.markdown(f'<div class="{star_cls}" style="margin:8px 0">{b.text}</div>', unsafe_allow_html=True)
            for s in by_block.get(b.id, []):
                if s.decision == "rejected": continue
                if s.action in ("insert_after","insert_before","replace_text") and s.new_text:
                    st.markdown(f'<div class="added" style="margin:5px 0 9px 14px">{s.new_text}</div>', unsafe_allow_html=True)
                elif s.action == "strike_text" and s.anchor_text:
                    st.markdown(f'<div class="removed" style="margin:5px 0 9px 14px">{s.anchor_text}</div>', unsafe_allow_html=True)
                elif s.action == "review":
                    st.caption("⚠ Suggestion à vérifier avant toute modification de ce passage")

    with right:
        st.markdown("### Modifications")
        if st.button("Accepter les changements sûrs ≥ 90 %", use_container_width=True):
            for s in suggestions:
                if s.auto_safe and s.confidence >= .9 and s.action not in ("review","no_change"):
                    s.decision = "accepted"
            st.rerun()
        for i,s in enumerate(suggestions):
            if s.action == "no_change":
                continue
            css = "sugg-review" if s.action == "review" else ("sugg-del" if s.action == "strike_text" else "sugg-add")
            label = {"insert_after":"AJOUT","insert_before":"AJOUT","replace_text":"MODIFICATION","strike_text":"SUPPRESSION","review":"À VÉRIFIER"}.get(s.action,s.action)
            st.markdown(f'<div class="sugg {css}"><b>{label}</b> <span class="conf">· {int(s.confidence*100)} %</span><br><span class="small">{s.reason}</span><br><br><b>Preuve</b> <span class="ts">{fmt_time(s.timestamp_start)}</span><br><span class="small">{s.evidence}</span></div>', unsafe_allow_html=True)
            c1,c2,c3 = st.columns(3)
            with c1:
                if st.button("Accepter", key=f"a-{i}", use_container_width=True, disabled=s.action=="review"):
                    s.decision="accepted"; st.rerun()
            with c2:
                if st.button("Rejeter", key=f"r-{i}", use_container_width=True):
                    s.decision="rejected"; st.rerun()
            with c3:
                st.write("✅" if s.decision=="accepted" else ("✕" if s.decision=="rejected" else "…"))

    st.divider()
    e1,e2,e3 = st.columns([1.2,1,1])
    accepted = [s for s in suggestions if s.decision == "accepted"]
    with e1:
        st.markdown(f"**{len(accepted)} modification(s) acceptée(s)** · les incertitudes ne sont jamais exportées automatiquement.")
    with e2:
        if st.session_state.docx_bytes:
            try:
                exported, warnings = apply_suggestions(st.session_state.docx_bytes, suggestions, os.getenv("DOCX_HIGHLIGHT_COLOR","cyan"))
                st.download_button("Exporter le Word actualisé", exported, file_name="fiche_actualisee.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True, type="primary")
                for w in warnings: st.warning(w)
            except Exception as e:
                st.error(f"Export impossible : {e}")
        else:
            st.button("Export Word indisponible en démo", disabled=True, use_container_width=True)
    with e3:
        report = "\n".join([f"- {s.action} · {int(s.confidence*100)}% · {s.reason}" for s in suggestions])
        st.download_button("Télécharger le rapport", report.encode("utf-8"), "rapport_modifications.txt", use_container_width=True)
