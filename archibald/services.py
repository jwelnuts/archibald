from __future__ import annotations

from datetime import date, timedelta

from django.db.models import Sum

from core.models import Payee
from income.models import IncomeSource
from planner.models import PlannerItem
from projects.models import Category, Customer, Project, ProjectNote
from routines.models import Routine, RoutineCheck, RoutineItem
from subscriptions.models import Account, Subscription, SubscriptionOccurrence, Tag
from todo.models import Task
from transactions.models import Transaction


PROJECT_STRUCTURE = (
    "Struttura MIO (sintesi): "
    "Transactions collegano Account, Currency, Category, Project, Payee, IncomeSource e Tag; "
    "Subscriptions generano SubscriptionOccurrence e possono collegarsi a Transaction; "
    "Routines -> RoutineItem -> RoutineCheck; "
    "Projects con Customer, Category e ProjectNote; "
    "PlannerItem collega Project/Category; "
    "Task gestisce todo; "
    "Payee/IncomeSource sono anagrafiche; "
    "Account/Tag/Currency gestiscono conti e classificazioni."
)

INTENT_KEYWORDS = {
    "overview": {"panoramica", "overview", "riepilogo", "sommario", "dashboard", "stato generale", "status"},
    "routines": {"routine", "routines", "rituale", "rituali"},
    "tasks": {"todo", "task", "compito", "compiti", "attivita", "attività", "promemoria"},
    "planner": {"planner", "pianifica", "pianificato", "piano", "calendario", "scadenza", "scadenze"},
    "subscriptions": {"abbonamento", "abbonamenti", "subscriptions", "ricorrenza", "ricorrenze"},
    "transactions": {
        "transazioni",
        "movimenti",
        "transaction",
        "spese",
        "uscite",
        "entrate",
        "income",
        "outcome",
        "budget",
        "costi",
        "pagamenti",
    },
    "projects": {"progetto", "progetti", "clienti", "categorie", "category", "customer"},
    "accounts": {"conti", "account", "cassa", "carte", "bank"},
}


def detect_intents(prompt: str) -> set[str]:
    text = (prompt or "").lower()
    intents: set[str] = set()
    for key, keywords in INTENT_KEYWORDS.items():
        if any(word in text for word in keywords):
            intents.add(key)
    return intents


def _current_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _base_capabilities_message() -> str:
    return (
        "App disponibili: Income, Outcome, Transactions, Subscriptions, Planner, Projects, Todo, Routines, Workbench. "
        "Puoi chiedere sintesi, dettagli e azioni su questi dati."
    )


def _fmt_currency_totals(rows) -> str:
    parts = []
    for row in rows:
        total = row.get("total") or 0
        code = row.get("currency__code") or "-"
        parts.append(f"{total:.2f} {code}")
    return ", ".join(parts) if parts else "0"


def _routine_context(user) -> str:
    week_start = _current_week_start()
    routines = Routine.objects.filter(owner=user, is_active=True).order_by("name")
    items = (
        RoutineItem.objects.filter(owner=user, is_active=True, routine__in=routines)
        .select_related("routine")
        .order_by("routine__name", "weekday", "time_start", "title")
    )
    if not routines.exists():
        return f"Nessuna routine attiva trovata per la settimana che inizia il {week_start.isoformat()}."

    checks = RoutineCheck.objects.filter(owner=user, week_start=week_start, item__in=items)
    check_map = {check.item_id: check.status for check in checks}

    routine_map = {}
    for item in items:
        status = check_map.get(item.id, RoutineCheck.Status.PLANNED)
        summary = routine_map.setdefault(
            item.routine_id,
            {
                "name": item.routine.name,
                "total": 0,
                "done": 0,
                "skipped": 0,
                "planned": 0,
            },
        )
        summary["total"] += 1
        if status == RoutineCheck.Status.DONE:
            summary["done"] += 1
        elif status == RoutineCheck.Status.SKIPPED:
            summary["skipped"] += 1
        else:
            summary["planned"] += 1

    total_items = len(items)
    total_done = sum(r["done"] for r in routine_map.values())
    total_skipped = sum(r["skipped"] for r in routine_map.values())
    total_planned = sum(r["planned"] for r in routine_map.values())

    lines = [
        f"Settimana corrente da {week_start.isoformat()}.",
        f"Routine attive: {routines.count()}. Attività attive: {total_items}.",
        f"Stato complessivo: {total_done} completate, {total_planned} pianificate, {total_skipped} saltate.",
        "Dettaglio per routine:",
    ]
    for summary in routine_map.values():
        lines.append(
            f"- {summary['name']}: {summary['done']} completate, "
            f"{summary['planned']} pianificate, {summary['skipped']} saltate "
            f"(totale {summary['total']})."
        )
    return "\n".join(lines)


def _project_context(user) -> str:
    today = date.today()
    week_start = _current_week_start()
    month_start = today.replace(day=1)
    next_week = today + timedelta(days=7)

    accounts_active = Account.objects.filter(owner=user, is_active=True).count()
    tags_count = Tag.objects.filter(owner=user).count()
    payees_count = Payee.objects.filter(owner=user).count()
    income_sources_count = IncomeSource.objects.filter(owner=user).count()

    projects_active = Project.objects.filter(owner=user, is_archived=False).count()
    projects_archived = Project.objects.filter(owner=user, is_archived=True).count()
    customers_count = Customer.objects.filter(owner=user).count()
    categories_count = Category.objects.filter(owner=user).count()
    notes_count = ProjectNote.objects.filter(owner=user).count()

    subs_active = Subscription.objects.filter(owner=user, status=Subscription.Status.ACTIVE).count()
    subs_paused = Subscription.objects.filter(owner=user, status=Subscription.Status.PAUSED).count()
    subs_due = SubscriptionOccurrence.objects.filter(owner=user, due_date__range=(today, next_week)).count()

    tx_month = Transaction.objects.filter(owner=user, date__range=(month_start, today))
    tx_income = tx_month.filter(tx_type=Transaction.Type.INCOME).count()
    tx_expense = tx_month.filter(tx_type=Transaction.Type.EXPENSE).count()
    tx_transfer = tx_month.filter(tx_type=Transaction.Type.TRANSFER).count()

    tasks_open = Task.objects.filter(owner=user, status=Task.Status.OPEN).count()
    tasks_progress = Task.objects.filter(owner=user, status=Task.Status.IN_PROGRESS).count()
    tasks_done = Task.objects.filter(owner=user, status=Task.Status.DONE).count()

    planner_planned = PlannerItem.objects.filter(owner=user, status=PlannerItem.Status.PLANNED).count()
    planner_done = PlannerItem.objects.filter(owner=user, status=PlannerItem.Status.DONE).count()
    planner_skipped = PlannerItem.objects.filter(owner=user, status=PlannerItem.Status.SKIPPED).count()

    routines_active = Routine.objects.filter(owner=user, is_active=True).count()
    routine_items = RoutineItem.objects.filter(owner=user, is_active=True).count()
    routine_checks = RoutineCheck.objects.filter(owner=user, week_start=week_start).count()

    lines = [
        PROJECT_STRUCTURE,
        "Dati disponibili (utente corrente):",
        f"- Conti attivi: {accounts_active}. Tag: {tags_count}. Payee: {payees_count}. Fonti reddito: {income_sources_count}.",
        f"- Progetti attivi: {projects_active}, archiviati: {projects_archived}. Clienti: {customers_count}. Categorie: {categories_count}. Note progetto: {notes_count}.",
        f"- Abbonamenti attivi: {subs_active}, in pausa: {subs_paused}. Scadenze prossimi 7 giorni: {subs_due}.",
        f"- Transazioni mese corrente: entrate {tx_income}, uscite {tx_expense}, trasferimenti {tx_transfer}.",
        f"- Todo: aperti {tasks_open}, in corso {tasks_progress}, completati {tasks_done}.",
        f"- Planner: pianificate {planner_planned}, completate {planner_done}, saltate {planner_skipped}.",
        f"- Routines: attive {routines_active}, attivita attive {routine_items}, check settimana corrente {routine_checks}.",
    ]
    return "\n".join(lines)


def _transactions_context(user) -> str:
    today = date.today()
    month_start = today.replace(day=1)
    tx_month = Transaction.objects.filter(owner=user, date__range=(month_start, today))
    expenses = (
        tx_month.filter(tx_type=Transaction.Type.EXPENSE)
        .values("currency__code")
        .annotate(total=Sum("amount"))
        .order_by("currency__code")
    )
    incomes = (
        tx_month.filter(tx_type=Transaction.Type.INCOME)
        .values("currency__code")
        .annotate(total=Sum("amount"))
        .order_by("currency__code")
    )
    transfers = tx_month.filter(tx_type=Transaction.Type.TRANSFER).count()
    recent = list(
        tx_month.select_related("currency", "category", "project")
        .order_by("-date", "-created_at")[:5]
    )

    lines = [
        f"Transazioni del mese (da {month_start.isoformat()} a oggi):",
        f"- Spese: {_fmt_currency_totals(expenses)}.",
        f"- Entrate: {_fmt_currency_totals(incomes)}.",
        f"- Trasferimenti: {transfers}.",
    ]
    if recent:
        lines.append(
            "Ultime transazioni: "
            + "; ".join(
                f"{t.get_tx_type_display()} {t.amount} {t.currency.code} ({t.date})"
                for t in recent
            )
        )
    return "\n".join(lines)


def _subscriptions_context(user) -> str:
    today = date.today()
    next_week = today + timedelta(days=7)
    next_month = today + timedelta(days=30)

    active = Subscription.objects.filter(owner=user, status=Subscription.Status.ACTIVE).count()
    paused = Subscription.objects.filter(owner=user, status=Subscription.Status.PAUSED).count()
    due_week = SubscriptionOccurrence.objects.filter(owner=user, due_date__range=(today, next_week)).count()
    due_month = SubscriptionOccurrence.objects.filter(owner=user, due_date__range=(today, next_month)).count()
    upcoming = list(
        SubscriptionOccurrence.objects.filter(owner=user, due_date__range=(today, next_week))
        .select_related("subscription", "currency")
        .order_by("due_date")[:5]
    )

    lines = [
        f"Abbonamenti: attivi {active}, in pausa {paused}.",
        f"Scadenze prossimi 7 giorni: {due_week}. Prossimi 30 giorni: {due_month}.",
    ]
    if upcoming:
        lines.append(
            "Prossime scadenze: "
            + "; ".join(
                f"{o.subscription.name} {o.amount} {o.currency.code} ({o.due_date})"
                for o in upcoming
            )
        )
    return "\n".join(lines)


def _tasks_context(user) -> str:
    today = date.today()
    next_week = today + timedelta(days=7)

    open_count = Task.objects.filter(owner=user, status=Task.Status.OPEN).count()
    progress = Task.objects.filter(owner=user, status=Task.Status.IN_PROGRESS).count()
    done = Task.objects.filter(owner=user, status=Task.Status.DONE).count()
    due_soon = Task.objects.filter(owner=user, due_date__range=(today, next_week)).count()
    upcoming = list(
        Task.objects.filter(owner=user, due_date__range=(today, next_week))
        .order_by("due_date")[:5]
    )

    lines = [
        f"Todo: aperti {open_count}, in corso {progress}, completati {done}.",
        f"Task in scadenza 7 giorni: {due_soon}.",
    ]
    if upcoming:
        lines.append(
            "Scadenze vicine: " + "; ".join(f"{t.title} ({t.due_date})" for t in upcoming)
        )
    return "\n".join(lines)


def _planner_context(user) -> str:
    today = date.today()
    next_week = today + timedelta(days=7)

    planned = PlannerItem.objects.filter(owner=user, status=PlannerItem.Status.PLANNED).count()
    done = PlannerItem.objects.filter(owner=user, status=PlannerItem.Status.DONE).count()
    skipped = PlannerItem.objects.filter(owner=user, status=PlannerItem.Status.SKIPPED).count()
    due_soon = PlannerItem.objects.filter(owner=user, due_date__range=(today, next_week)).count()
    upcoming = list(
        PlannerItem.objects.filter(owner=user, due_date__range=(today, next_week))
        .order_by("due_date")[:5]
    )

    lines = [
        f"Planner: pianificate {planned}, completate {done}, saltate {skipped}.",
        f"Item in scadenza 7 giorni: {due_soon}.",
    ]
    if upcoming:
        lines.append(
            "Scadenze vicine: " + "; ".join(f"{p.title} ({p.due_date})" for p in upcoming)
        )
    return "\n".join(lines)


def _projects_context(user) -> str:
    active = Project.objects.filter(owner=user, is_archived=False).count()
    archived = Project.objects.filter(owner=user, is_archived=True).count()
    customers = Customer.objects.filter(owner=user).count()
    categories = Category.objects.filter(owner=user).count()
    recent = list(Project.objects.filter(owner=user).order_by("-created_at")[:5])

    lines = [
        f"Progetti attivi: {active}, archiviati: {archived}.",
        f"Clienti: {customers}. Categorie: {categories}.",
    ]
    if recent:
        lines.append(
            "Progetti recenti: "
            + "; ".join(f"{p.name} ({'archiviato' if p.is_archived else 'attivo'})" for p in recent)
        )
    return "\n".join(lines)


def build_context_messages(user, prompt: str) -> list[dict]:
    intents = detect_intents(prompt)
    if not intents:
        intents = {"overview"}

    messages = [{"role": "system", "content": _base_capabilities_message()}]

    if "overview" in intents:
        messages.append({"role": "system", "content": _project_context(user)})
    if "routines" in intents:
        messages.append({"role": "system", "content": _routine_context(user)})
    if "transactions" in intents:
        messages.append({"role": "system", "content": _transactions_context(user)})
    if "subscriptions" in intents:
        messages.append({"role": "system", "content": _subscriptions_context(user)})
    if "tasks" in intents:
        messages.append({"role": "system", "content": _tasks_context(user)})
    if "planner" in intents:
        messages.append({"role": "system", "content": _planner_context(user)})
    if "projects" in intents:
        messages.append({"role": "system", "content": _projects_context(user)})

    return messages


def build_insight_cards(user, kind: str) -> list[dict]:
    today = date.today()
    next_week = today + timedelta(days=7)
    month_start = today.replace(day=1)
    kind = (kind or "overview").lower()

    if kind == "expenses":
        expenses = (
            Transaction.objects.filter(owner=user, tx_type=Transaction.Type.EXPENSE, date__range=(month_start, today))
            .values("currency__code")
            .annotate(total=Sum("amount"))
            .order_by("currency__code")
        )
        count = Transaction.objects.filter(
            owner=user, tx_type=Transaction.Type.EXPENSE, date__range=(month_start, today)
        ).count()
        return [
            {"label": "Spese mese", "value": _fmt_currency_totals(expenses), "sub": "dal 1° del mese"},
            {"label": "Transazioni", "value": str(count), "sub": "uscite registrate"},
        ]

    if kind == "tasks":
        open_count = Task.objects.filter(owner=user, status=Task.Status.OPEN).count()
        progress = Task.objects.filter(owner=user, status=Task.Status.IN_PROGRESS).count()
        due_soon = Task.objects.filter(owner=user, due_date__range=(today, next_week)).count()
        return [
            {"label": "Aperti", "value": str(open_count), "sub": "todo"},
            {"label": "In corso", "value": str(progress), "sub": "task attivi"},
            {"label": "Scadenze 7gg", "value": str(due_soon), "sub": "priorità"},
        ]

    if kind == "subscriptions":
        active = Subscription.objects.filter(owner=user, status=Subscription.Status.ACTIVE).count()
        due_week = SubscriptionOccurrence.objects.filter(owner=user, due_date__range=(today, next_week)).count()
        return [
            {"label": "Attivi", "value": str(active), "sub": "abbonamenti"},
            {"label": "Scadenze 7gg", "value": str(due_week), "sub": "in arrivo"},
        ]

    if kind == "planner":
        planned = PlannerItem.objects.filter(owner=user, status=PlannerItem.Status.PLANNED).count()
        due_soon = PlannerItem.objects.filter(owner=user, due_date__range=(today, next_week)).count()
        return [
            {"label": "Pianificati", "value": str(planned), "sub": "planner"},
            {"label": "Scadenze 7gg", "value": str(due_soon), "sub": "in arrivo"},
        ]

    if kind == "routines":
        routines_active = Routine.objects.filter(owner=user, is_active=True).count()
        today_items = RoutineItem.objects.filter(owner=user, is_active=True, weekday=today.weekday()).count()
        week_start = _current_week_start()
        done_week = RoutineCheck.objects.filter(
            owner=user, week_start=week_start, status=RoutineCheck.Status.DONE
        ).count()
        return [
            {"label": "Routine attive", "value": str(routines_active), "sub": "totale"},
            {"label": "Oggi", "value": str(today_items), "sub": "attività"},
            {"label": "Completate", "value": str(done_week), "sub": "settimana"},
        ]

    if kind == "projects":
        active = Project.objects.filter(owner=user, is_archived=False).count()
        customers = Customer.objects.filter(owner=user).count()
        return [
            {"label": "Progetti attivi", "value": str(active), "sub": "in corso"},
            {"label": "Clienti", "value": str(customers), "sub": "anagrafiche"},
        ]

    # overview
    expenses = (
        Transaction.objects.filter(owner=user, tx_type=Transaction.Type.EXPENSE, date__range=(month_start, today))
        .values("currency__code")
        .annotate(total=Sum("amount"))
        .order_by("currency__code")
    )
    open_tasks = Task.objects.filter(owner=user, status=Task.Status.OPEN).count()
    subs_due = SubscriptionOccurrence.objects.filter(owner=user, due_date__range=(today, next_week)).count()
    accounts_active = Account.objects.filter(owner=user, is_active=True).count()
    return [
        {"label": "Spese mese", "value": _fmt_currency_totals(expenses), "sub": "uscite registrate"},
        {"label": "Task aperti", "value": str(open_tasks), "sub": "todo"},
        {"label": "Scadenze 7gg", "value": str(subs_due), "sub": "abbonamenti"},
        {"label": "Conti attivi", "value": str(accounts_active), "sub": "account"},
    ]
