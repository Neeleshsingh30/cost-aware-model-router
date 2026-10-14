"""Streamlit interface for the Cost-Aware Multi-Model Router API."""

import csv
import io
import os
from datetime import date, datetime, time, timezone
from html import escape

import requests
import streamlit as st


API_BASE_URL = os.getenv("ROUTER_API_URL", "http://127.0.0.1:8001").rstrip("/")
REQUESTS_URL = f"{API_BASE_URL}/api/v1/requests"
LOGS_URL = f"{API_BASE_URL}/api/v1/dashboard/logs"
EXPECTED_COLUMNS = [
    "request_id", "timestamp", "task_type", "input_length",
    "complexity_score", "complexity_reasons", "initial_model",
    "final_model", "haiku_confidence", "escalated", "escalation_reason",
    "input_tokens", "output_tokens", "actual_cost",
    "sonnet_baseline_cost", "savings", "savings_percentage",
    "latency_ms", "request_status",
]
TASKS = {
    "Classification": "classification",
    "Extraction": "extraction",
    "Summarisation": "summarisation",
    "Question & answer": "qa",
}
SAMPLES = {
    "Classification": {
        "input": "I was charged twice for the same invoice.",
        "categories": "billing, technical, account, general",
    },
    "Extraction": {
        "input": "Contact Maya Shah at maya@example.com or +1 415 555 0198 to arrange the product demo.",
        "fields": "name, email, phone, purpose",
    },
    "Summarisation": {
        "input": "The router tries a lower-cost model for every request first. It checks whether the answer is complete and confident. If the task is complex or the first answer is uncertain, it escalates to a stronger model. Token usage is used to estimate cost and savings.",
    },
    "Question & answer": {
        "input": "The support team is available Monday through Friday, 9 AM to 5 PM. Billing questions are usually answered within two business days.",
        "question": "When is support available?",
    },
}


st.set_page_config(
    page_title="Cost-Aware Model Router",
    page_icon=":material/route:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes"}


def _parse_timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except (TypeError, ValueError):
        return None


def load_routing_logs():
    """Fetch request metadata from FastAPI. No prompt text is returned here."""
    try:
        response = requests.get(LOGS_URL, timeout=8)
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list):
            return None, "The dashboard endpoint returned an unexpected response."
        normalized = []
        for row in rows:
            item = {column: row.get(column) for column in EXPECTED_COLUMNS}
            item["actual_cost"] = _as_float(item.get("actual_cost"))
            item["sonnet_baseline_cost"] = _as_float(item.get("sonnet_baseline_cost"))
            item["savings"] = _as_float(item.get("savings"))
            item["input_tokens"] = _as_float(item.get("input_tokens"))
            item["output_tokens"] = _as_float(item.get("output_tokens"))
            item["complexity_score"] = _as_float(item.get("complexity_score"))
            item["latency_ms"] = _as_float(item.get("latency_ms"), None)
            item["haiku_confidence"] = _as_float(item.get("haiku_confidence"), None)
            item["escalated"] = _as_bool(item.get("escalated"))
            item["_timestamp"] = _parse_timestamp(item.get("timestamp"))
            normalized.append(item)
        normalized.sort(key=lambda row: row["_timestamp"] or datetime.min.replace(tzinfo=timezone.utc))
        return normalized, None
    except (requests.RequestException, ValueError) as error:
        return None, str(error)


def _show_backend_status():
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=2)
        response.raise_for_status()
        st.sidebar.badge("Backend connected", icon=":material/check_circle:", color="green")
    except requests.RequestException:
        st.sidebar.badge("Backend unavailable", icon=":material/error:", color="red")
        st.sidebar.caption(f"Expected API: {API_BASE_URL}")


def _select_sample():
    sample = st.session_state.get("sample_request")
    if sample in SAMPLES:
        st.session_state["task_type"] = sample
        for key in ("request_input", "request_categories", "request_fields", "request_question"):
            st.session_state[key] = ""
        values = SAMPLES[sample]
        st.session_state["request_input"] = values.get("input", "")
        st.session_state["request_categories"] = values.get("categories", "")
        st.session_state["request_fields"] = values.get("fields", "")
        st.session_state["request_question"] = values.get("question", "")


def _render_result(result):
    st.subheader("Latest result")
    st.caption(
        f"Request ID: {result.get('request_id', 'Unavailable')} · "
        f"Task: {result.get('task_type', 'Unavailable')} · "
        f"Status: {result.get('request_status', 'Unavailable')}"
    )
    if result.get("error"):
        st.error(f"Model request failed: {result['error']}")
    answer = result.get("answer") or ""
    with st.container(border=True):
        st.markdown("**Final answer**")
        if answer:
            st.success(answer)
        else:
            st.warning("No final answer was returned.")

    st.markdown("#### Routing and usage")
    with st.container(horizontal=True):
        st.metric("Initial model", result.get("initial_model") or "N/A", border=True)
        st.metric("Final model", result.get("final_model") or "N/A", border=True)
        st.metric("Escalated", "Yes" if result.get("escalated") else "No", border=True)
        st.metric("Confidence", f"{result['confidence']:.2f}" if result.get("confidence") is not None else "N/A", border=True)
        latency = result.get("latency_ms")
        st.metric("Model latency", f"{latency:,.0f} ms" if latency is not None else "N/A", border=True)
    with st.container(horizontal=True):
        usage_available = result.get("cost_available", True)
        st.metric("Input tokens", f"{result.get('input_tokens', 0):,}" if usage_available else "N/A", border=True)
        st.metric("Output tokens", f"{result.get('output_tokens', 0):,}" if usage_available else "N/A", border=True)
        actual = result.get("actual_cost")
        baseline = result.get("sonnet_baseline_cost")
        savings = result.get("savings")
        st.metric("Estimated cost", f"${actual:.8f}" if actual is not None else "Unavailable", border=True)
        st.metric("Strong-model baseline", f"${baseline:.8f}" if baseline is not None else "Unavailable", border=True)
    if not usage_available:
        st.info("Cost analysis is unavailable because the provider returned no token usage.")
    elif result.get("savings_percentage") is not None:
        st.metric("Estimated savings", f"${savings:.8f}", f"{result['savings_percentage']:.2f}% vs. strong-model baseline", border=True)
    if result.get("escalation_reason"):
        st.caption(f"Routing detail: {result['escalation_reason']}")
    if result.get("fast_answer"):
        with st.expander("Initial fast-model response"):
            st.write(result["fast_answer"])
    reasons = result.get("complexity_reasons") or []
    if reasons:
        with st.expander("Routing signals"):
            for reason in reasons:
                st.write(f"- {reason}")


def render_request_page():
    st.title("Run a model request")
    st.write("Submit a task and follow the routing decision, response, and estimated cost.")

    task_display = st.selectbox("Task type", list(TASKS), key="task_type")
    sample_options = ["Choose an example…", *SAMPLES.keys()]
    st.selectbox(
        "Try a sample request",
        sample_options,
        key="sample_request",
        on_change=_select_sample,
        help="Loads a ready-to-edit example for the selected task.",
    )
    task_type = TASKS[task_display]

    with st.form("request_form", border=True):
        input_label = "Context" if task_type == "qa" else "Input text"
        text_height = 190 if task_type in {"classification", "qa"} else 250
        input_text = st.text_area(
            input_label,
            key="request_input",
            height=text_height,
            placeholder="Paste or type the text you want the router to process…",
            max_chars=20000,
        )
        categories = None
        fields = None
        question = None
        if task_type == "classification":
            category_text = st.text_input(
                "Allowed categories",
                key="request_categories",
                placeholder="billing, technical, account, general",
                help="Separate category names with commas.",
            )
            categories = [value.strip() for value in category_text.split(",") if value.strip()]
        elif task_type == "extraction":
            field_text = st.text_input(
                "Fields to extract",
                key="request_fields",
                placeholder="name, email, phone",
                help="Separate field names with commas.",
            )
            fields = [value.strip() for value in field_text.split(",") if value.strip()]
        elif task_type == "qa":
            question = st.text_input("Question", key="request_question", placeholder="Ask a question about the context…")

        submitted = st.form_submit_button(
            "Run request",
            type="primary",
            icon=":material/arrow_forward:",
            width="stretch",
        )

    if submitted:
        if not input_text.strip():
            st.error("Enter some input text before running the request.")
            return
        if task_type == "classification" and not categories:
            st.error("Add at least one allowed category.")
            return
        if task_type == "extraction" and not fields:
            st.error("Add at least one field to extract.")
            return
        if task_type == "qa" and not (question or "").strip():
            st.error("Enter a question about the context.")
            return

        payload = {
            "task_type": task_type,
            "input_text": input_text,
            "categories": categories,
            "fields": fields,
            "question": question,
        }
        try:
            with st.status("Routing your request…", expanded=True) as status:
                st.write("Checking task complexity and model confidence.")
                response = requests.post(REQUESTS_URL, json=payload, timeout=180)
                response.raise_for_status()
                result = response.json()
                status.update(label="Request completed", state="complete", expanded=False)
            st.session_state["latest_result"] = result
        except requests.HTTPError as error:
            try:
                detail = error.response.json().get("detail", str(error))
            except (AttributeError, ValueError):
                detail = str(error)
            st.error(f"The request could not be completed: {detail}")
        except requests.RequestException as error:
            st.error(f"Could not reach FastAPI at {API_BASE_URL}. Start the backend and retry. Details: {error}")

    if st.session_state.get("latest_result"):
        _render_result(st.session_state["latest_result"])


def _filtered_rows(rows):
    st.subheader("Explore request history")
    models = sorted({str(row.get("final_model") or "Unknown") for row in rows})
    tasks = sorted({str(row.get("task_type") or "unknown") for row in rows})
    with st.popover("Filters", icon=":material/filter_list:"):
        selected_models = st.multiselect("Final model", models, default=models, key="dash_models")
        selected_tasks = st.multiselect("Task type", tasks, default=tasks, key="dash_tasks")
        escalated_only = st.toggle("Escalated requests only", key="dash_escalated")
        search = st.text_input("Search model or routing reason", key="dash_search").strip().lower()
    filtered = [
        row for row in rows
        if str(row.get("final_model") or "Unknown") in selected_models
        and str(row.get("task_type") or "unknown") in selected_tasks
        and (not escalated_only or row["escalated"])
        and (not search or search in str(row.get("final_model") or "").lower()
             or search in str(row.get("initial_model") or "").lower()
             or search in str(row.get("escalation_reason") or "").lower())
    ]
    return filtered


def _render_bar_chart(items, *, aria_label):
    """Render lightweight bars without Streamlit's Altair/pandas chart stack."""
    maximum = max((abs(value) for _, value, _ in items), default=0) or 1
    colors = ["#5B5BD6", "#19A974", "#FF9F43", "#E85D75", "#4C9AFF", "#9B6BDB"]
    rows_html = []
    for index, (label, value, display) in enumerate(items):
        width = max(0, min(100, abs(value) / maximum * 100))
        color = colors[index % len(colors)]
        rows_html.append(
            f'<div style="margin:0 0 16px" title="{escape(display)}">'
            f'<div style="display:flex;justify-content:space-between;gap:16px;margin-bottom:6px">'
            f'<span>{escape(str(label))}</span><strong>{escape(str(display))}</strong></div>'
            f'<div style="height:10px;border-radius:99px;background:#e9ecf5;overflow:hidden">'
            f'<div style="height:100%;width:{width:.2f}%;border-radius:99px;background:{color}"></div>'
            f'</div></div>'
        )
    st.markdown(
        f'<div role="img" aria-label="{escape(aria_label)}">{"".join(rows_html)}</div>',
        unsafe_allow_html=True,
    )


def _render_savings_chart(points):
    """Render a small accessible SVG trend chart without optional chart DLLs."""
    if not points:
        st.caption("No timestamped requests are available for this chart.")
        return
    width, height = 820, 250
    left, right, top, bottom = 64, 18, 22, 42
    values = [point[1] for point in points]
    maximum = max(values) or 1
    plot_width = width - left - right
    plot_height = height - top - bottom
    coords = []
    for index, (label, value) in enumerate(points):
        x = left + (plot_width * index / max(1, len(points) - 1))
        y = top + plot_height * (1 - value / maximum)
        coords.append((x, y, label, value))
    grid = []
    for fraction in (0, 0.5, 1):
        y = top + plot_height * fraction
        amount = maximum * (1 - fraction)
        grid.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#e9ecf5"/>'
            f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" fill="#697386" font-size="11">${amount:.5f}</text>'
        )
    line_points = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in coords)
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#5B5BD6">'
        f'<title>{escape(label)} · ${value:.8f}</title></circle>'
        for x, y, label, value in coords
    )
    label_indices = sorted(set([0, len(coords) // 2, len(coords) - 1]))
    labels = "".join(
        f'<text x="{coords[i][0]:.1f}" y="{height-12}" text-anchor="middle" fill="#697386" font-size="10">'
        f'{escape(coords[i][2])}</text>' for i in label_indices
    )
    st.markdown(
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Cumulative estimated savings over time" '
        f'style="width:100%;height:auto;display:block">'
        f'{"".join(grid)}<polyline points="{line_points}" fill="none" stroke="#5B5BD6" '
        f'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>{dots}{labels}</svg>',
        unsafe_allow_html=True,
    )


def render_dashboard_page():
    st.title("Routing analytics")
    st.write("Filter request history, compare estimated costs, and inspect routing outcomes.")
    if st.button("Refresh dashboard", icon=":material/refresh:"):
        st.rerun()

    rows, error = load_routing_logs()
    if error:
        st.warning(f"Could not load dashboard data. Check the FastAPI service at {API_BASE_URL}.")
        with st.expander("Connection details"):
            st.code(error)
        return
    if not rows:
        st.info("No requests have been recorded yet. Run a request to start building your dashboard.")
        return

    filtered = _filtered_rows(rows)
    if not filtered:
        st.info("No requests match these filters. Update the filters to see results.")
        return

    total = len(filtered)
    successful = sum(
        str(row.get("request_status") or "").lower() == "success"
        or (not row.get("request_status") and bool(row["input_tokens"] or row["output_tokens"]))
        for row in filtered
    )
    fast = sum("deepseek" in str(row.get("final_model") or "").lower() for row in filtered)
    strong = sum(
        bool(row.get("final_model"))
        and "deepseek" not in str(row.get("final_model") or "").lower()
        for row in filtered
    )
    escalated = sum(row["escalated"] for row in filtered)
    failed = sum(
        str(row.get("request_status") or "").lower() == "failed"
        or (not row.get("request_status") and not (row["input_tokens"] or row["output_tokens"]))
        for row in filtered
    )
    latencies = [row["latency_ms"] for row in filtered if row.get("latency_ms") is not None]
    average_latency = sum(latencies) / len(latencies) if latencies else None
    actual_cost = sum(row["actual_cost"] for row in filtered)
    baseline = sum(row["sonnet_baseline_cost"] for row in filtered)
    savings = sum(row["savings"] for row in filtered)
    success_rate = successful / total * 100 if total else 0
    savings_rate = savings / baseline * 100 if baseline > 0 else 0

    with st.container(horizontal=True):
        st.metric("Requests", f"{total:,}", border=True)
        st.metric("Success rate", f"{success_rate:.1f}%", f"{successful} successful", border=True)
        st.metric("Fast-model share", f"{fast / total * 100:.1f}%", f"{fast} requests", border=True)
        st.metric("Strong-model requests", f"{strong:,}", border=True)
        st.metric("Escalations", f"{escalated:,}", f"{escalated / total * 100:.1f}% of requests", border=True)
    with st.container(horizontal=True):
        st.metric("Average latency", f"{average_latency:,.0f} ms" if average_latency is not None else "N/A", border=True)
        st.metric("Failed requests", f"{failed:,}", border=True)
        st.metric("Estimated spend", f"${actual_cost:.8f}", border=True)
        st.metric("Strong-model baseline", f"${baseline:.8f}", border=True)
        st.metric("Estimated savings", f"${savings:.8f}", f"{savings_rate:.2f}%", border=True)

    view = st.segmented_control(
        "Dashboard view",
        ["Overview", "Costs", "Requests"],
        default="Overview",
        key="dashboard_view",
        width="stretch",
    )
    if view == "Overview":
        st.subheader("Model usage")
        model_counts = {}
        for row in filtered:
            model = str(row.get("final_model") or "Unknown")
            model_counts[model] = model_counts.get(model, 0) + 1
        model_data = [{"Model": model, "Requests": count} for model, count in sorted(model_counts.items(), key=lambda pair: pair[1], reverse=True)]
        _render_bar_chart(
            [(item["Model"], item["Requests"], f'{item["Requests"]:,} requests') for item in model_data],
            aria_label="Request count by final model",
        )

        task_counts = {}
        for row in filtered:
            task = str(row.get("task_type") or "unknown")
            task_counts[task] = task_counts.get(task, 0) + 1
        left, right = st.columns(2)
        with left:
            with st.container(border=True):
                st.markdown("**Requests by task**")
                _render_bar_chart(
                    [(task, count, f"{count:,} requests") for task, count in sorted(task_counts.items())],
                    aria_label="Request volume by task type",
                )
        with right:
            with st.container(border=True):
                st.markdown("**Outcomes**")
                _render_bar_chart(
                    [("Successful", successful, f"{successful:,} requests"),
                     ("No token usage", total - successful, f"{total - successful:,} requests")],
                    aria_label="Successful requests compared with requests without token usage",
                )

    elif view == "Costs":
        st.subheader("Estimated cost comparison")
        _render_bar_chart(
            [("Cost-aware router", actual_cost, f"${actual_cost:.8f}"),
             ("Always strong model", baseline, f"${baseline:.8f}")],
            aria_label="Estimated router spend compared with always using the strong model",
        )
        timestamped = [row for row in filtered if row["_timestamp"]]
        if timestamped:
            cumulative = 0.0
            trend = []
            for row in timestamped:
                cumulative += row["savings"]
                trend.append((row["_timestamp"].strftime("%m-%d %H:%M"), cumulative))
            st.subheader("Savings over time")
            _render_savings_chart(trend)
        st.caption("Costs are estimates based on the model pricing configured for this project.")

    else:
        st.subheader("Request history")
        query = st.text_input("Find a request", placeholder="Search task, model, or routing reason…", key="request_table_search").strip().lower()
        history = []
        for row in reversed(filtered):
            record = {
                "Request ID": row.get("request_id") or "",
                "Time": row.get("timestamp") or "",
                "Task": row.get("task_type") or "unknown",
                "Initial model": row.get("initial_model") or "N/A",
                "Final model": row.get("final_model") or "N/A",
                "Escalated": "Yes" if row["escalated"] else "No",
                "Status": row.get("request_status") or "Unknown",
                "Latency (ms)": row.get("latency_ms"),
                "Input tokens": int(row["input_tokens"]),
                "Output tokens": int(row["output_tokens"]),
                "Estimated cost (USD)": row["actual_cost"],
                "Savings (USD)": row["savings"],
                "Routing reason": row.get("escalation_reason") or "",
            }
            if not query or query in " ".join(map(str, record.values())).lower():
                history.append(record)
        if not history:
            st.info("No requests match this search.")
        for record in history:
            title = f'{record["Time"]} · {record["Task"]} · {record["Final model"]}'
            with st.expander(title):
                if record["Request ID"]:
                    st.caption(f'Request ID: {record["Request ID"]}')
                with st.container(horizontal=True):
                    st.metric("Estimated cost", f'${record["Estimated cost (USD)"]:.8f}', border=True)
                    st.metric("Savings", f'${record["Savings (USD)"]:.8f}', border=True)
                    st.metric("Escalated", record["Escalated"], border=True)
                    st.metric("Status", record["Status"], border=True)
                    latency = record["Latency (ms)"]
                    st.metric("Latency", f"{latency:,.0f} ms" if latency is not None else "N/A", border=True)
                st.write(f'**Initial model:** {record["Initial model"]}')
                st.write(f'**Token usage:** {record["Input tokens"]:,} input · {record["Output tokens"]:,} output')
                if record["Routing reason"]:
                    st.caption(record["Routing reason"])
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(history[0].keys()) if history else ["Time"])
        writer.writeheader()
        writer.writerows(history)
        st.download_button(
            "Download filtered history",
            buffer.getvalue(),
            file_name="routing-history.csv",
            mime="text/csv",
            icon=":material/download:",
        )


with st.sidebar:
    st.title("Router console")
    st.caption("Cost-aware multi-model routing")
    st.divider()
    _show_backend_status()
    page = st.radio(
        "Workspace",
        ["Run request", "Analytics dashboard"],
        format_func=lambda item: f":material/{'play_arrow' if item == 'Run request' else 'monitoring'}: {item}",
        label_visibility="collapsed",
        key="workspace_page",
    )
    st.divider()
    st.caption("Requests are sent to the FastAPI backend. Provider credentials stay on the backend.")

if page == "Run request":
    render_request_page()
else:
    render_dashboard_page()
