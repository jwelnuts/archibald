from projects.models import Category, Project


def build_placeholder_name(model_cls, owner, raw_value: str, max_length: int) -> str:
    value = (raw_value or "").strip()
    base_name = "Nuovo"
    if value:
        base_name = f"Nuovo - {value}"

    base_name = base_name[:max_length]
    candidate = base_name
    index = 2

    while model_cls.objects.filter(owner=owner, name=candidate).exists():
        suffix = f" ({index})"
        truncated = base_name[: max(1, max_length - len(suffix))]
        candidate = f"{truncated}{suffix}"
        index += 1

    return candidate


def create_quick_project(owner, raw_value: str):
    return Project.objects.create(
        owner=owner,
        name=build_placeholder_name(Project, owner, raw_value, 120),
        description="Creato da inserimento rapido. Da completare nel modulo Projects.",
        is_archived=False,
    )


def create_quick_category(owner, raw_value: str):
    return Category.objects.create(
        owner=owner,
        name=build_placeholder_name(Category, owner, raw_value, 80),
    )
