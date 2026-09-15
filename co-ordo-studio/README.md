# Co-Ordo Studio — V1 autonome

Outil de relecture/actualisation de fiches Word à partir d'un MP3 de cours.

## Ce qui fonctionne
- Upload MP3 + DOCX N-1.
- Extraction conservatrice du DOCX depuis son XML natif.
- Transcription horodatée via OpenAI si `OPENAI_API_KEY` est configurée.
- Analyse pédagogique comparative via OpenAI si la clé est présente.
- Mode démo complet sans clé.
- Interface 3 panneaux : transcription / fiche / suggestions.
- Acceptation/rejet des changements.
- Export DOCX par patches locaux appliqués directement au package Word original.
- Ajouts : gras + surlignage bleu/cyan.
- Suppressions : barré + surlignage bleu/cyan uniquement si la cible XML est sûre.
- Toute cible ambiguë est laissée intacte et signalée.

## Lancer
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# renseigner OPENAI_API_KEY dans .env pour le vrai pipeline IA
streamlit run app.py
```

## Philosophie de sécurité DOCX
Le fichier Word N-1 reste le document maître. Le code ouvre le `.docx` comme archive ZIP et modifie seulement `word/document.xml` pour les opérations acceptées. Toutes les autres parties du package Word sont recopiées byte-for-byte. Cela évite de reconstruire la fiche depuis du Markdown/HTML.

Les suppressions/remplacements ne sont appliqués automatiquement que lorsque le texte cible peut être localisé de façon suffisamment sûre dans un run Word. Sinon, la fiche n'est pas modifiée et un avertissement est généré.

## Variables
- `OPENAI_API_KEY`
- `OPENAI_TRANSCRIBE_MODEL` (défaut: `whisper-1`, utilisé pour les timestamps de segment)
- `OPENAI_ANALYSIS_MODEL` (défaut: `gpt-5.6-terra`)
- `DOCX_HIGHLIGHT_COLOR` (défaut: `cyan`)

## Suite logique
1. Tester avec une vraie fiche N-1 et un MP3.
2. Ajuster le prompt à partir de tes décisions réelles.
3. Ajouter persistance Supabase + comptes + historique.
4. Ajouter une vraie preview Word haute fidélité côté serveur.
5. Ajouter le module de contrôle des fiches reçues des référents/QCM.
