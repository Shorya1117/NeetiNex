"""
Renders the scheme comparison table inside the chat.

The table data comes from the backend (rule engine). This file only shows it:
  scheme | status | your matching conditions | other conditions / still needed |
  where to apply | documents | official source
"""

import csv
import html
import io

import streamlit as st

STATUS_STYLE = {
    "ELIGIBLE": ("#16a34a", "Eligible"),
    "UNVERIFIED": ("#d97706", "Likely - verify"),
    "NEED_MORE_INFORMATION": ("#2563eb", "Need more info"),
    "UNCHECKABLE": ("#6b7280", "Check manually"),
}

TABLE_CSS = """
<style>
.nx-wrap{overflow-x:auto;margin:8px 0;}
table.nx{border-collapse:collapse;width:100%;min-width:1150px;font-size:13px;}
table.nx th{background:rgba(124,92,255,.25);text-align:left;padding:8px 10px;
            border:1px solid rgba(255,255,255,.15);position:sticky;top:0;}
table.nx td{vertical-align:top;padding:8px 10px;border:1px solid rgba(255,255,255,.12);}
table.nx ul{margin:0;padding-left:16px;}
.nx-pill{display:inline-block;padding:2px 8px;border-radius:10px;color:#fff;
         font-size:12px;font-weight:600;white-space:nowrap;}
.nx-dept{opacity:.7;font-size:12px;}
.nx-ok{color:#22c55e;} .nx-no{opacity:.85;}
</style>
"""


def _e(text) -> str:
    return html.escape(str(text))


def _list(items, icon="") -> str:
    if not items:
        return "<span style='opacity:.6'>-</span>"
    return "<ul>" + "".join(f"<li>{icon}{_e(i)}</li>" for i in items) + "</ul>"


def _status_key(row) -> str:
    if row["status"] == "UNVERIFIED" and not row["your_match"]:
        return "UNCHECKABLE"
    return row["status"]


def _apply_cell(row) -> str:
    parts = []
    if row["where_to_apply"]:
        parts.append(_list(row["where_to_apply"]))
    for link in row["apply_links"]:
        parts.append(f'<a href="{_e(link)}" target="_blank">{_e(link)}</a>')
    return "".join(parts) or "<span style='opacity:.6'>Not specified in source</span>"


def _other_cell(row) -> str:
    parts = []
    if row["need_to_tell"]:
        parts.append("<b>Tell me:</b>" + _list(row["need_to_tell"], "❓ "))
    if row["other_conditions"]:
        extra = row["other_conditions_total"] - len(row["other_conditions"])
        parts.append("<b>Also check:</b>" + _list(row["other_conditions"]) +
                     (f"<i>+{extra} more</i>" if extra > 0 else ""))
    return "".join(parts) or "<span style='opacity:.6'>-</span>"


def build_table_html(rows) -> str:
    head = ("<tr><th>#</th><th>Scheme</th><th>Status</th><th>Your conditions that match</th>"
            "<th>Other conditions / still needed</th><th>Where to apply</th>"
            "<th>Documents required</th><th>Source</th></tr>")
    body = []
    for i, r in enumerate(rows, 1):
        color, label = STATUS_STYLE[_status_key(r)]
        source = (f'<a href="{_e(r["source_url"])}" target="_blank">Official page</a>'
                  if r.get("source_url") else "-")
        body.append(
            f"<tr><td>{i}</td>"
            f"<td><b>{_e(r['scheme_name'])}</b><div class='nx-dept'>{_e(r['department'])}</div></td>"
            f"<td><span class='nx-pill' style='background:{color}'>{label}</span></td>"
            f"<td>{_list(r['your_match'], '✅ ')}</td>"
            f"<td>{_other_cell(r)}</td>"
            f"<td>{_apply_cell(r)}</td>"
            f"<td>{_list(r['documents'])}</td>"
            f"<td>{source}</td></tr>")
    return f"{TABLE_CSS}<div class='nx-wrap'><table class='nx'>{head}{''.join(body)}</table></div>"


def table_to_csv(rows) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Scheme", "Department", "Status", "Your matching conditions",
                     "Other conditions", "Where to apply", "Documents", "Source"])
    for r in rows:
        writer.writerow([r["scheme_name"], r["department"], r["status_label"],
                         " | ".join(r["your_match"]), " | ".join(r["other_conditions"]),
                         " > ".join(r["where_to_apply"] + r["apply_links"]),
                         " | ".join(r["documents"]), r.get("source_url") or ""])
    return out.getvalue()


def render_eligibility_table(message: dict, key: str) -> None:
    """Show profile used, comparison table, excluded schemes, CSV download."""
    table = message.get("table") or {}
    rows = table.get("rows") or []

    if message.get("profile_summary"):
        st.caption("Details used: " + " • ".join(message["profile_summary"]))
    for note in message.get("assumptions") or []:
        st.caption(f"ℹ️ {note}")

    if rows:
        st.markdown(build_table_html(rows), unsafe_allow_html=True)
        counts = table.get("counts", {})
        st.caption(
            f"Eligible: {counts.get('ELIGIBLE', 0)} • Likely (verify): "
            f"{counts.get('UNVERIFIED', 0)} • "
            f"Need more info: {counts.get('NEED_MORE_INFORMATION', 0)} • "
            f"Check manually: {counts.get('UNCHECKABLE', 0)} • "
            f"Showing {len(rows)} of {table.get('total_matching', len(rows))}")
        st.download_button("⬇️ Download table (CSV)", table_to_csv(rows),
                           file_name="neetinex_schemes.csv", mime="text/csv",
                           key=f"dl_{key}")
    if table.get("not_eligible"):
        with st.expander(f"❌ {table['not_eligible_count']} related scheme(s) you do NOT qualify for"):
            for item in table["not_eligible"]:
                st.markdown(f"- **{item['scheme_name']}** — {item['reason']}")
