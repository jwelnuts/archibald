# ai_lab

## Scopo
L'app `ai_lab` e il laboratorio personale AI.
Serve per tracciare studio/esperimenti e configurare il profilo comportamentale di Archibald.

## Funzionalita principali
- CRUD voci studio (`LabEntry`) con area, stato, prompt, risultato e next step.
- Dashboard con filtro stato e card di avanzamento.
- Sezione `personal-lab` per configurazione persona Archibald.
- Sandbox prompt per testare risposte con debug payload OpenAI.

## Modelli chiave
- `LabEntry`: voce di studio o esperimento AI.
- `ArchibaldPersonaConfig`: profilo stile/tono/strategie cognitive di Archibald.
- `ArchibaldInstructionState`: stato istruzioni salvate per owner.

## View / Endpoint principali
- `GET /ai-lab/`: dashboard entries.
- `GET/POST /ai-lab/personal-lab/`: configurazione persona + test sandbox.
- `GET/POST /ai-lab/api/add`
- `GET/POST /ai-lab/api/update?id=<id>`
- `GET/POST /ai-lab/api/remove?id=<id>`

## Template/UI principali
- `ai_lab/dashboard.html`
- `ai_lab/personal_lab.html`
- `ai_lab/add_item.html`
- `ai_lab/update_item.html`
- `ai_lab/remove_item.html`

## Integrazioni con altre app
- `archibald`: usa prompting e client OpenAI di Archibald per il sandbox.

## Casi d'uso reali
- Tenere traccia dei progressi su prompting/RAG/embeddings.
- Tarare il comportamento di Archibald su stile operativo personale.
- Validare velocemente output AI prima di applicare modifiche globali.

## Note operative
- Il sandbox puo includere debug strutturato della chiamata OpenAI.
- Preset e boolean cognitivi permettono tuning fine della persona.

## Copertura test esistente
- `AiLabViewsTests`

## Debito tecnico / TODO
- Versionare i profili persona per rollback rapido.
- Introdurre comparazione side-by-side tra preset.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
