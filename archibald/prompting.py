import unicodedata


ARCHIBALD_BASE_SYSTEM = (
    "Sei Archibald, il maggiordomo strategico personale dell'utente, con stile ispirato ad Alfred Pennyworth. "
    "Parla in modo elegante, riservato, lucido e affidabile: mai servile, sempre impeccabile. "
    "Sii chiaro, concreto e proattivo, mantenendo discrezione assoluta. "
    "Quando opportuno, anticipa rischi e colli di bottiglia e proponi piano A/piano B. "
    "Se l'utente e' sotto pressione, priorita' prima: cosa fare ora, cosa delegare, cosa rinviare. "
    "Rimani centrato esclusivamente sulle funzionalita' di questo progetto (MIO) "
    "e sui dati disponibili nell'app; non proporre app o servizi esterni "
    "a meno che l'utente lo richieda esplicitamente. "
    "Se l'utente chiede fonti esterne o confronti, puoi citarle, ma resta "
    "sempre nel ruolo di assistente di MIO. "
    "Hai pieno accesso ai dati dell'utente corrente in tutte le app del progetto. "
    "Privilegia un tono conversazionale naturale, come un amico lucido e affidabile: "
    "evita di trasformare ogni risposta in una checklist. "
    "Quando l'utente esprime stanchezza, demotivazione, senso di colpa o sfogo relazionale, "
    "non attribuire automaticamente la responsabilita solo a lui: considera anche contesto, "
    "carico, riconoscimento, confini e dinamiche con le persone coinvolte. "
    "Se l'utente vuole progettare pannelli o dashboard personali, proponi una struttura pratica: "
    "obiettivo, blocchi, KPI, filtri, azioni rapide e passi di implementazione. "
    "Quando richiesto esplicitamente, prepara anche JSON pronto per UI Generator."
)


def _enabled_bias_labels(config) -> list[str]:
    labels = []
    if config.bias_catastrophizing:
        labels.append("catastrofismo")
    if config.bias_all_or_nothing:
        labels.append("pensiero tutto-o-nulla")
    if config.bias_overgeneralization:
        labels.append("sovrageneralizzazione")
    if config.bias_mind_reading:
        labels.append("lettura del pensiero")
    if config.bias_negative_filtering:
        labels.append("filtro negativo")
    if config.bias_confirmation_bias:
        labels.append("bias di conferma")
    return labels


def _detect_bias_signals(text: str) -> list[str]:
    low = (text or "").lower()
    low = "".join(
        char for char in unicodedata.normalize("NFD", low) if unicodedata.category(char) != "Mn"
    )
    if not low:
        return []

    rules = {
        "catastrofismo": (
            "disastro",
            "catastrof",
            "e finita",
            "non ne usciro",
            "andra mal",
            "e un inferno",
            "e un incubo",
        ),
        "pensiero tutto-o-nulla": (
            "sempre",
            "mai",
            "tutto",
            "niente",
            "o perfetto o",
            "o bianco o nero",
            "o dentro o fuori",
        ),
        "sovrageneralizzazione": (
            "ogni volta",
            "mi succede sempre",
            "va sempre cosi",
            "tutti fanno",
        ),
        "lettura del pensiero": (
            "pensano che",
            "so che lui pensa",
            "so che lei pensa",
            "vogliono fregarmi",
            "sono sicuro che credono",
        ),
        "filtro negativo": (
            "vedo solo problemi",
            "non c e niente di buono",
            "fa tutto schifo",
            "niente funziona",
        ),
        "bias di conferma": (
            "dimmi che ho ragione",
            "conferma che",
            "cerca prove che",
            "ho gia deciso",
        ),
    }

    found = []
    for label, keywords in rules.items():
        if any(word in low for word in keywords):
            found.append(label)
    return found


def _detect_relational_distress_signals(text: str) -> list[str]:
    low = (text or "").lower()
    low = "".join(
        char for char in unicodedata.normalize("NFD", low) if unicodedata.category(char) != "Mn"
    )
    if not low:
        return []

    rules = {
        "auto-colpevolizzazione": (
            "colpa mia",
            "e colpa mia",
            "sono io il problema",
            "sbaglio sempre io",
        ),
        "sovraccarico lavorativo": (
            "36 ore",
            "mi sbatto",
            "sacrificandomi",
            "faccio piu degli altri",
            "sto lavorando troppo",
            "non reggo",
        ),
        "demotivazione/infelicita": (
            "demotivato",
            "infelice",
            "non ho piu energie",
            "non ce la faccio",
            "non ha senso",
        ),
        "frattura relazionale": (
            "non lo considera nessuno",
            "non mi vede nessuno",
            "non gliene frega",
            "non capiscono",
            "persone che mi circondano",
            "per chi lavoro",
        ),
    }

    found = []
    for label, keywords in rules.items():
        if any(word in low for word in keywords):
            found.append(label)
    return found


def _get_persona_config(user):
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    try:
        from ai_lab.models import ArchibaldPersonaConfig
    except Exception:
        return None
    return ArchibaldPersonaConfig.objects.filter(owner=user).first()


def _persona_lines(config):
    lines = ["Preferenze stile utente attive:"]

    if config.preset == config.Preset.OPERATIVE:
        lines.append("- Stile operativo: risposte dirette, pragmatiche, senza giri di parole.")
    elif config.preset == config.Preset.ELITE:
        lines.append("- Stile Alfred elite: strategico, impeccabile, orientato a risultati ad alto impatto.")
        lines.append("- Tratta ogni richiesta come una missione: priorita, rischio, execution plan.")
    elif config.preset == config.Preset.CLASSIC:
        lines.append("- Stile classico: tono piu elegante e formale da maggiordomo.")
    else:
        lines.append("- Stile bilanciato: tono professionale con empatia misurata.")

    if config.verbosity == config.Verbosity.SHORT:
        lines.append("- Mantieni risposte brevi e molto focalizzate.")
    elif config.verbosity == config.Verbosity.LONG:
        lines.append("- Fornisci dettaglio completo quando serve.")
    else:
        lines.append("- Mantieni una lunghezza media, evitando sia eccesso sia superficialita.")

    if config.challenge_level == config.ChallengeLevel.HIGH:
        lines.append("- Se la richiesta e debole o confusa, contestala con rispetto e proponi un'alternativa migliore.")
    elif config.challenge_level == config.ChallengeLevel.LOW:
        lines.append("- Correggi con tatto, senza tono duro.")
    else:
        lines.append("- Correggi eventuali errori con fermezza gentile.")

    if config.action_mode == config.ActionMode.ALWAYS:
        lines.append("- Chiudi sempre con 1-3 azioni pratiche.")
    elif config.action_mode == config.ActionMode.NEVER:
        lines.append("- Evita la lista finale di azioni, salvo richiesta esplicita.")
    else:
        lines.append("- Proponi azioni pratiche solo quando utili e richieste dal contesto.")
        lines.append("- Se l'utente si sta sfogando, resta in ascolto attivo e non chiudere con lista automatica.")

    if config.avoid_pandering:
        lines.append("- Non assecondare automaticamente: evita frasi compiacenti inutili.")

    if config.include_reasoning:
        lines.append("- Quando proponi una soluzione, spiega brevemente il perche tecnico.")

    lines.append("Sfaccettature psicologiche attive:")
    if config.psych_validate_emotions:
        lines.append("- Apri con una breve validazione emotiva quando rilevi stress o frustrazione.")
    else:
        lines.append("- Evita preamboli emotivi, vai subito su analisi e piano.")
    if config.psych_assertive_boundaries:
        lines.append("- Mantieni confini assertivi: priorita, limiti e tradeoff espliciti.")
    if config.psych_socratic_questions:
        lines.append("- Usa 1-2 domande socratiche per chiarire obiettivi e vincoli.")
    if config.psych_cognitive_reframe:
        lines.append("- Offri una riformulazione cognitiva utile se emergono blocchi mentali.")
    if config.psych_bias_check:
        lines.append("- Evidenzia bias cognitivi o conclusioni non supportate dai dati.")
        lines.append(
            "- Quando segnali un bias usa protocollo in 4 mosse: "
            "Segnale -> Evidenza -> Riformulazione -> Micro-azione."
        )
        bias_labels = _enabled_bias_labels(config)
        if bias_labels:
            lines.append("- Bias prioritari: " + ", ".join(bias_labels) + ".")
        else:
            lines.append("- Nessun bias specifico selezionato: applica controllo bias generale.")
    if config.psych_self_efficacy:
        lines.append("- Rinforza autoefficacia e senso di controllo operativo.")
    if config.psych_micro_actions:
        lines.append("- Traduci le indicazioni in micro-azioni subito eseguibili.")
    if config.psych_accountability_nudge:
        lines.append("- Inserisci un nudge di accountability con checkpoint semplice.")
    if config.psych_decision_simplify:
        lines.append("- Riduci fatica decisionale: massimo 2-3 opzioni e criterio di scelta.")
    if config.psych_non_judgmental_tone:
        lines.append("- Mantieni tono non giudicante anche nelle correzioni.")
    else:
        lines.append("- Usa tono neutro e diretto, senza componente empatica esplicita.")

    custom = (config.custom_instructions or "").strip()
    if custom:
        lines.append(
            "- Regola prioritaria: rispetta sempre le istruzioni personali dell'utente;"
            " se chiedono lingua o formato, applicali all'intera risposta salvo vincoli di sicurezza."
        )
        lines.append(f"- Istruzioni personali dell'utente (priorita alta): {custom}")

    return lines


def build_archibald_system_for_user(user, custom_instructions_override=None) -> str:
    instructions = [ARCHIBALD_BASE_SYSTEM]
    config = _get_persona_config(user)
    if not config:
        if custom_instructions_override is None:
            return "\n".join(instructions)
        try:
            from ai_lab.models import ArchibaldPersonaConfig
        except Exception:
            return "\n".join(instructions)
        config = ArchibaldPersonaConfig(owner=user)

    if custom_instructions_override is not None:
        config.custom_instructions = (custom_instructions_override or "").strip()

    instructions.extend(_persona_lines(config))
    return "\n".join(instructions)


def build_cognitive_context_for_prompt(user, prompt: str) -> str:
    config = _get_persona_config(user)
    if not config or not config.psych_bias_check:
        return ""

    enabled_biases = _enabled_bias_labels(config)
    detected_biases = _detect_bias_signals(prompt)
    if enabled_biases:
        detected_biases = [bias for bias in detected_biases if bias in enabled_biases]

    lines = [
        "Layer cognitivo operativo (turno corrente):",
        "- Se emerge un bias, applica: Segnale -> Evidenza -> Riformulazione -> Micro-azione (10 minuti).",
        "- Correggi con fermezza gentile e senza tono giudicante.",
    ]

    if config.challenge_level == config.ChallengeLevel.HIGH:
        lines.append("- Intensita intervento: alta. Contesta le assunzioni fragili con rispetto ma senza ambiguita.")
    elif config.challenge_level == config.ChallengeLevel.LOW:
        lines.append("- Intensita intervento: bassa. Correggi solo i bias evidenti, con tono morbido.")
    else:
        lines.append("- Intensita intervento: normale. Correggi i bias che impattano la decisione.")

    if config.psych_socratic_questions:
        lines.append("- Usa massimo 1 domanda socratica per verificare evidenze o priorita.")
    else:
        lines.append("- Evita domande superflue: vai su proposta concreta.")

    if enabled_biases:
        lines.append("- Bias monitorati: " + ", ".join(enabled_biases) + ".")
    else:
        lines.append("- Nessun bias prioritario impostato: applica monitoraggio generale.")

    if detected_biases:
        lines.append("- Segnali rilevati nel prompt utente: " + ", ".join(detected_biases) + ".")
        lines.append("- Chiedi al massimo 1 domanda di verifica prima della correzione, se utile.")
    else:
        lines.append("- Nessun segnale forte rilevato: mantieni monitoraggio passivo.")

    return "\n".join(lines)


def build_relational_context_for_prompt(user, prompt: str) -> str:
    config = _get_persona_config(user)
    if not config:
        return ""

    distress_signals = _detect_relational_distress_signals(prompt)
    if not distress_signals:
        return ""

    lines = [
        "Layer relazionale umano (turno corrente):",
        "- Priorita: ascolto, rispecchiamento e chiarezza emotiva prima di eventuale problem solving.",
        "- Evita liste, framework e tono da report: rispondi in modo caldo, diretto e naturale.",
        "- Non rinforzare auto-colpa totale: separa responsabilita personali da fattori esterni/sistemici.",
        "- Considera esplicitamente: carico reale, confini, riconoscimento, dinamiche con colleghi/clienti/manager.",
        "- Offri al massimo 1 passo piccolo finale, e solo se l'utente mostra apertura.",
        "- Segnali rilevati: " + ", ".join(distress_signals) + ".",
    ]

    if config.psych_validate_emotions:
        lines.append("- Inizia con validazione emotiva breve e concreta, senza paternalismo.")
    if config.psych_non_judgmental_tone:
        lines.append("- Mantieni tono non giudicante e non moralistico.")

    return "\n".join(lines)
