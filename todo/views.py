from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import TaskForm
from .models import Task

# Create your views here.
@login_required
def dashboard(request):
    user = request.user
    open_tasks = (
        Task.objects.filter(owner=user, status=Task.Status.OPEN)
        .order_by("due_date", "created_at")[:5]
    )
    counts = {
        "open": Task.objects.filter(owner=user, status=Task.Status.OPEN).count(),
        "in_progress": Task.objects.filter(owner=user, status=Task.Status.IN_PROGRESS).count(),
        "done": Task.objects.filter(owner=user, status=Task.Status.DONE).count(),
    }
    return render(
        request,
        "todo/dashboard.html",
        {
            "open_tasks": open_tasks,
            "counts": counts,
        },
    )


@login_required
def add_task(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.owner = request.user
            task.save()
            return redirect("/todo/")
    else:
        form = TaskForm()
    return render(request, "todo/add_task.html", {"form": form})


@login_required
def remove_task(request):
    task_id = request.GET.get("id")
    task = None
    if task_id:
        task = get_object_or_404(Task, id=task_id, owner=request.user)
        if request.method == "POST":
            task.delete()
            return redirect("/todo/")
    tasks = Task.objects.filter(owner=request.user).order_by("-created_at")[:20]
    return render(request, "todo/remove_task.html", {"task": task, "tasks": tasks})


@login_required
def update_task(request):
    task_id = request.GET.get("id")
    task = None
    if task_id:
        task = get_object_or_404(Task, id=task_id, owner=request.user)
        if request.method == "POST":
            form = TaskForm(request.POST, instance=task)
            if form.is_valid():
                form.save()
                return redirect("/todo/")
        else:
            form = TaskForm(instance=task)
        return render(request, "todo/update_task.html", {"form": form, "task": task})
    tasks = Task.objects.filter(owner=request.user).order_by("-created_at")[:20]
    return render(request, "todo/update_task.html", {"tasks": tasks})
