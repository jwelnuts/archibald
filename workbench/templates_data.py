from __future__ import annotations

BASE_TEMPLATE = """{% load static %}
<!doctype html>
<html lang="it">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=0.7">
    <title>__APP_TITLE__</title>
    <link rel="stylesheet" href="{% static '__APP_NAME__/styles.css' %}">
  </head>
  <body>
    <main class="shell">
      <header class="top">
        <h1>__APP_TITLE__</h1>
        <a class="btn" href="/">Dashboard</a>
      </header>
      {% block content %}{% endblock %}
    </main>
  </body>
</html>
"""


DASHBOARD_TEMPLATE = """{% extends '__APP_NAME__/base.html' %}

{% block content %}
  <section class="panel">
    <p>Modulo: __APP_TITLE__</p>
    <p>Gestione: __MODEL_PLURAL__</p>
    <div class="actions">
      <a class="btn primary" href="./api/add">Nuovo</a>
    </div>
  </section>

  <section class="panel">
    {% if rows %}
      <table class="table">
        <thead>
          <tr>
            {% for field in display_fields %}
              <th>{{ field }}</th>
            {% endfor %}
            <th>Azioni</th>
          </tr>
        </thead>
        <tbody>
          {% for row in rows %}
            <tr>
              {% for value in row.values %}
                <td>{{ value }}</td>
              {% endfor %}
              <td>
                <a class="btn" href="./api/update?id={{ row.id }}">Modifica</a>
                <a class="btn" href="./api/remove?id={{ row.id }}">Rimuovi</a>
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    {% else %}
      <div class="warn">Nessun elemento disponibile.</div>
    {% endif %}
  </section>
{% endblock %}
"""


FORM_TEMPLATE = """{% extends '__APP_NAME__/base.html' %}

{% block content %}
  <section class="panel">
    <h2>__ACTION__</h2>
    <form method="post" class="form">
      {% csrf_token %}
      {{ form.as_p }}
      <div class="actions">
        <button class="btn primary" type="submit">Salva</button>
        <a class="btn" href="../">Annulla</a>
      </div>
    </form>
  </section>
{% endblock %}
"""


REMOVE_TEMPLATE = """{% extends '__APP_NAME__/base.html' %}

{% block content %}
  <section class="panel">
    <h2>Rimuovi elemento</h2>
    <p>Confermi l'eliminazione di: <strong>{{ item }}</strong>?</p>
    <form method="post">
      {% csrf_token %}
      <div class="actions">
        <button class="btn primary" type="submit">Conferma</button>
        <a class="btn" href="../">Annulla</a>
      </div>
    </form>
  </section>
{% endblock %}
"""