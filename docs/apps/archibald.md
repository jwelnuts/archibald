---
title: archibald
tags: [app, archibald, removed]
aliases: [ai, chatbot, assistant, diary]
---

# Archibald App (RIMOSSO)

> **Stato**: Questa app è stata rimossa dal progetto il 27 Aprile 2026.

AI-powered personal assistant powered by OpenAI. La funzionalità email di salvataggio appunti è stata preservata in [[archibald_mail]].

## Modelli Rimossi

| Model | Descrizione | Key Fields |
|-------|-------------|------------|
| `ArchibaldThread` | Conversation threads | title, is_active, kind, openai_conversation_id |
| `ArchibaldMessage` | Messages in threads | thread, role, content, is_favorite |
| `ArchibaldPersonaConfig` | AI persona settings | preset, verbosity, challenge_level, psych options |
| `ArchibaldInstructionState` | Dynamic instructions | name, instructions_text |

## URL Patterns (Rimossi)

| Route | Name | Description |
|-------|------|-------------|
| `/` | archibald-dashboard | Chat interface |
| `/messages` | archibald-messages | Messages API |
| `/favorite` | archibald-favorite | Toggle favorite |
| `/insights` | archibald-insights | Insights view |
| `/temp/new` | archibald-temp-new | Create temp thread |
| `/temp/remove` | archibald-temp-remove | Remove temp thread |
| `/quick` | archibald-quick | Quick chat API |

## Feature Rimosse

- OpenAI-powered conversations (GPT-5)
- Configurable AI persona
- Psychological support features
- Bias detection and correction
- Thread management (diary vs temporary)
- Context building da dati MIO

## Cosa Mantenere

- [[archibald_mail]] - Funzionalità email (separata e indipendente)
- [[memory_stock]] - Salvataggio appunti via email ($MEMORY, $IDEA flag)