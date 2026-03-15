from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="archibald-mail-dashboard"),
    path("flags/", views.flag_rules, name="archibald-mail-flag-rules"),
    path("flags/add", views.add_flag_rule, name="archibald-mail-flag-add"),
    path("flags/<int:rule_id>/edit", views.edit_flag_rule, name="archibald-mail-flag-edit"),
    path("flags/<int:rule_id>/remove", views.remove_flag_rule, name="archibald-mail-flag-remove"),
    path("inbox/", views.inbound_queue, name="archibald-mail-inbox"),
    path("inbox/<int:message_id>/apply", views.apply_inbound_message, name="archibald-mail-inbox-apply"),
    path("inbox/<int:message_id>/ignore", views.ignore_inbound_message, name="archibald-mail-inbox-ignore"),
    path("inbox/<int:message_id>/reopen", views.reopen_inbound_message, name="archibald-mail-inbox-reopen"),
]
