"""WeasyPrint-based bilingual PDF report generator.

Produces a water-balance report from pre-fetched data dicts.
Caller is responsible for fetching data; this module only renders.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from jinja2 import BaseLoader, Environment

# ---------------------------------------------------------------------------
# Data contract
# ---------------------------------------------------------------------------

@dataclass
class ReportPeriod:
    from_date: str   # ISO date string "YYYY-MM-DD"
    to_date: str


@dataclass
class DmaSummaryRow:
    code: str
    name: str
    siv_m3: float
    scv_m3: float
    nrw_m3: float
    nrw_pct: float
    flag_level: str


@dataclass
class WorklistRow:
    rank: int
    dma_code: str
    dma_name: str | None
    estimated_loss_m3: float | None
    savings_mad: float | None
    confidence_score: int
    alert_type: str
    status: str


@dataclass
class ReportData:
    tenant_name: str
    period: ReportPeriod
    lang: str                                   # "fr" | "ar"
    dma_rows: list[DmaSummaryRow] = field(default_factory=list)
    worklist_rows: list[WorklistRow] = field(default_factory=list)
    generated_at: str = ""                      # ISO datetime


# ---------------------------------------------------------------------------
# i18n strings embedded (no file I/O in domain layer)
# ---------------------------------------------------------------------------

_LABELS: dict[str, dict[str, str]] = {
    "fr": {
        "title": "Rapport Eau Non Facturée",
        "tenant": "Régie",
        "period": "Période",
        "generated": "Généré le",
        "dma_table": "Bilan par Zone de Mesure (Top 10)",
        "code": "Code",
        "name": "Nom",
        "siv": "SIV (m³)",
        "scv": "SCV (m³)",
        "nrw_m3": "ENF (m³)",
        "nrw_pct": "Taux ENF (%)",
        "flag": "Niveau",
        "worklist_table": "Plan de Réparation Prioritaire",
        "rank": "Rang",
        "loss": "Perte (m³/mois)",
        "savings": "Économies (MAD/mois)",
        "confidence": "Confiance (%)",
        "alert": "Alerte",
        "status": "Statut",
        "normal": "Normal",
        "warning": "Attention",
        "critical": "Critique",
        "no_data": "Aucune donnée disponible.",
    },
    "ar": {
        "title": "تقرير المياه غير المُدرّة للإيراد",
        "tenant": "الجهة",
        "period": "الفترة",
        "generated": "تاريخ الإصدار",
        "dma_table": "ملخص مناطق القياس (أعلى 10)",
        "code": "الرمز",
        "name": "الاسم",
        "siv": "SIV (م³)",
        "scv": "SCV (م³)",
        "nrw_m3": "المياه غير المُدرّة (م³)",
        "nrw_pct": "النسبة (%)",
        "flag": "المستوى",
        "worklist_table": "قائمة الإصلاحات ذات الأولوية",
        "rank": "الترتيب",
        "loss": "الخسارة (م³/شهر)",
        "savings": "الوفورات (درهم/شهر)",
        "confidence": "الثقة (%)",
        "alert": "نوع التنبيه",
        "status": "الحالة",
        "normal": "طبيعي",
        "warning": "تحذير",
        "critical": "حرج",
        "no_data": "لا توجد بيانات متاحة.",
    },
}

# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_TEMPLATE = """<!DOCTYPE html>
<html lang="{{ lang }}" dir="{{ 'rtl' if lang == 'ar' else 'ltr' }}">
<head>
<meta charset="UTF-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&family=Inter:wght@400;600;700&display=swap');

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: {% if lang == 'ar' %}'Cairo', sans-serif{% else %}'Inter', sans-serif{% endif %};
    font-size: 10pt;
    color: #1f2937;
    padding: 2cm 2.5cm;
    direction: {{ 'rtl' if lang == 'ar' else 'ltr' }};
  }
  h1 { font-size: 18pt; font-weight: 700; color: #0284c7; margin-bottom: 0.3cm; }
  h2 { font-size: 12pt; font-weight: 600; color: #374151; margin: 0.6cm 0 0.3cm; }
  .meta { font-size: 9pt; color: #6b7280; margin-bottom: 0.8cm; }
  .meta span { margin-{{ 'left' if lang == 'ar' else 'right' }}: 1.5cm; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 0.5cm; }
  th {
    background: #0284c7; color: #ffffff;
    padding: 4pt 6pt; font-weight: 600; font-size: 9pt;
    text-align: {{ 'right' if lang == 'ar' else 'left' }};
  }
  td { padding: 4pt 6pt; border-bottom: 1pt solid #e5e7eb; font-size: 9pt; }
  tr:nth-child(even) td { background: #f9fafb; }
  .badge-normal { color: #16a34a; }
  .badge-warning { color: #d97706; }
  .badge-critical { color: #dc2626; font-weight: 600; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .no-data { color: #9ca3af; font-style: italic; padding: 0.5cm 0; }
  @page { margin: 0; }
</style>
</head>
<body>
<h1>{{ L.title }}</h1>
<div class="meta">
  <span>{{ L.tenant }}: <strong>{{ data.tenant_name }}</strong></span>
  <span>{{ L.period }}: {{ data.period.from_date }} → {{ data.period.to_date }}</span>
  <span>{{ L.generated }}: {{ data.generated_at }}</span>
</div>

<!-- DMA summary -->
<h2>{{ L.dma_table }}</h2>
{% if data.dma_rows %}
<table>
  <thead>
    <tr>
      <th>{{ L.code }}</th><th>{{ L.name }}</th>
      <th class="num">{{ L.siv }}</th><th class="num">{{ L.scv }}</th>
      <th class="num">{{ L.nrw_m3 }}</th><th class="num">{{ L.nrw_pct }}</th>
      <th>{{ L.flag }}</th>
    </tr>
  </thead>
  <tbody>
  {% for row in data.dma_rows[:10] %}
    <tr>
      <td><strong>{{ row.code }}</strong></td>
      <td>{{ row.name }}</td>
      <td class="num">{{ '{:,.0f}'.format(row.siv_m3) }}</td>
      <td class="num">{{ '{:,.0f}'.format(row.scv_m3) }}</td>
      <td class="num">{{ '{:,.0f}'.format(row.nrw_m3) }}</td>
      <td class="num {{ 'badge-critical' if row.nrw_pct >= 40 else ('badge-warning' if row.nrw_pct >= 25 else 'badge-normal') }}">
        {{ '{:.1f}'.format(row.nrw_pct) }} %
      </td>
      <td class="badge-{{ row.flag_level }}">{{ L[row.flag_level] }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
<p class="no-data">{{ L.no_data }}</p>
{% endif %}

<!-- Worklist -->
<h2>{{ L.worklist_table }}</h2>
{% if data.worklist_rows %}
<table>
  <thead>
    <tr>
      <th>{{ L.rank }}</th><th>{{ L.code }}</th><th>{{ L.name }}</th>
      <th class="num">{{ L.loss }}</th><th class="num">{{ L.savings }}</th>
      <th class="num">{{ L.confidence }}</th>
      <th>{{ L.alert }}</th><th>{{ L.status }}</th>
    </tr>
  </thead>
  <tbody>
  {% for row in data.worklist_rows %}
    <tr>
      <td><strong>#{{ row.rank }}</strong></td>
      <td>{{ row.dma_code }}</td>
      <td>{{ row.dma_name or '—' }}</td>
      <td class="num">{{ '{:,.0f}'.format(row.estimated_loss_m3 or 0) }}</td>
      <td class="num">{{ '{:,.0f}'.format(row.savings_mad or 0) }}</td>
      <td class="num">{{ row.confidence_score }}%</td>
      <td>{{ row.alert_type }}</td>
      <td>{{ row.status }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
<p class="no-data">{{ L.no_data }}</p>
{% endif %}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Render function
# ---------------------------------------------------------------------------

def render_pdf(report: ReportData) -> bytes:
    """Render report data to PDF bytes using WeasyPrint."""
    from weasyprint import HTML  # deferred so import only happens in worker

    labels = _LABELS.get(report.lang, _LABELS["fr"])
    env = Environment(loader=BaseLoader())
    template = env.from_string(_TEMPLATE)
    html_str = template.render(data=report, L=labels, lang=report.lang)
    return HTML(string=html_str).write_pdf()
