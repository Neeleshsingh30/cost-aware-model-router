# import streamlit as st

# from prompt_builder import build_prompt
# from router import route_request


# # =========================================================
# # Page Configuration
# # =========================================================

# st.set_page_config(
#     page_title="Cost-Aware Multi-Model Router",
#     page_icon="🤖",
#     layout="wide",
# )


# # =========================================================
# # Page Header
# # =========================================================

# st.title("Cost-Aware Multi-Model Router")

# st.subheader(
#     "Route every request to the cheapest model that can actually handle it."
# )

# st.divider()


# # =========================================================
# # Task Type
# # =========================================================

# task_type_display = st.selectbox(
#     "Task Type",
#     [
#         "Classification",
#         "Extraction",
#         "Summarisation",
#         "Q&A",
#     ],
# )

# task_type_map = {
#     "Classification": "classification",
#     "Extraction": "extraction",
#     "Summarisation": "summarisation",
#     "Q&A": "qa",
# }

# task_type = task_type_map[task_type_display]


# # =========================================================
# # Task-Specific Inputs
# # =========================================================

# input_text = ""

# categories = None
# fields = None
# question = None


# # ---------------------------------------------------------
# # Classification
# # ---------------------------------------------------------

# if task_type == "classification":

#     input_text = st.text_area(
#         "Input",
#         height=250,
#         placeholder=(
#             "Enter the text you want to classify..."
#         ),
#     )

#     categories_text = st.text_input(
#         "Allowed Categories",
#         placeholder="Example: billing, technical, account, general",
#     )

#     if categories_text.strip():
#         categories = [
#             category.strip()
#             for category in categories_text.split(",")
#             if category.strip()
#         ]


# # ---------------------------------------------------------
# # Extraction
# # ---------------------------------------------------------

# elif task_type == "extraction":

#     input_text = st.text_area(
#         "Text",
#         height=300,
#         placeholder=(
#             "Enter the text from which you want "
#             "to extract information..."
#         ),
#     )

#     fields_text = st.text_input(
#         "Fields to Extract",
#         placeholder="Example: name, email, phone",
#     )

#     if fields_text.strip():
#         fields = [
#             field.strip()
#             for field in fields_text.split(",")
#             if field.strip()
#         ]


# # ---------------------------------------------------------
# # Summarisation
# # ---------------------------------------------------------

# elif task_type == "summarisation":

#     input_text = st.text_area(
#         "Text to Summarise",
#         height=350,
#         placeholder=(
#             "Enter the text you want to summarise..."
#         ),
#     )


# # ---------------------------------------------------------
# # Q&A
# # ---------------------------------------------------------

# elif task_type == "qa":

#     input_text = st.text_area(
#         "Context",
#         height=300,
#         placeholder=(
#             "Enter the context that should be used "
#             "to answer the question..."
#         ),
#     )

#     question = st.text_input(
#         "Question",
#         placeholder="Enter your question...",
#     )


# st.divider()


# # =========================================================
# # Run Request
# # =========================================================

# run_request = st.button(
#     "Run Request",
#     type="primary",
#     use_container_width=True,
# )


# if run_request:

#     # -----------------------------------------------------
#     # Basic Input Validation
#     # -----------------------------------------------------

#     if not input_text.strip():

#         st.error(
#             "Please enter some input before running the request."
#         )

#         st.stop()

#     if task_type == "classification":

#         if not categories:
#             st.error(
#                 "Please provide at least one classification category."
#             )

#             st.stop()

#     if task_type == "extraction":

#         if not fields:
#             st.error(
#                 "Please provide at least one field to extract."
#             )

#             st.stop()

#     if task_type == "qa":

#         if not question or not question.strip():
#             st.error(
#                 "Please enter a question."
#             )

#             st.stop()

#     # -----------------------------------------------------
#     # Build Task Prompt
#     # -----------------------------------------------------

#     try:

#         prompt = build_prompt(
#             task_type=task_type,
#             input_text=input_text,
#             categories=categories,
#             fields=fields,
#             question=question,
#         )

#     except ValueError as error:

#         st.error(
#             f"Unable to build the request: {error}"
#         )

#         st.stop()

#     # -----------------------------------------------------
#     # Run Router
#     # -----------------------------------------------------

#     try:

#         with st.spinner(
#             "Analyzing request and selecting the appropriate model..."
#         ):

#             result = route_request(
#                 text=prompt,
#                 task_type=task_type,
#             )

#     except Exception as error:

#         st.error(
#             "The request could not be completed."
#         )

#         st.exception(error)

#         st.stop()

#     # -----------------------------------------------------
#     # Check Router Error
#     # -----------------------------------------------------

#     if result.get("error"):

#         st.warning(
#             f"Request completed with a routing error: "
#             f"{result['error']}"
#         )

#     # =====================================================
#     # Results
#     # =====================================================

#     st.divider()

#     st.header("Result")

#     # -----------------------------------------------------
#     # Final Answer
#     # -----------------------------------------------------

#     st.markdown("### Final Answer")

#     answer = result.get(
#         "answer",
#         "",
#     )

#     if answer:
#         st.success(answer)

#     else:
#         st.warning(
#             "No final answer was returned."
#         )

#     # =====================================================
#     # Model Information
#     # =====================================================

#     st.markdown("### Model Routing")

#     col1, col2, col3 = st.columns(3)

#     with col1:

#         st.metric(
#             "Initial Model",
#             result.get(
#                 "initial_model",
#                 "N/A",
#             ),
#         )

#     with col2:

#         st.metric(
#             "Final Model",
#             result.get(
#                 "final_model",
#                 "N/A",
#             ),
#         )

#     with col3:

#         escalated = result.get(
#             "escalated",
#             False,
#         )

#         st.metric(
#             "Escalated",
#             "Yes" if escalated else "No",
#         )

#     # =====================================================
#     # Routing Analysis
#     # =====================================================

#     st.markdown("### Routing Analysis")

#     col1, col2 = st.columns(2)

#     with col1:

#         complexity_score = result.get(
#             "complexity_score",
#             0.0,
#         )

#         st.metric(
#             "Complexity Score",
#             f"{complexity_score:.2f}",
#         )

#     with col2:

#         confidence = result.get(
#             "confidence",
#             None,
#         )

#         if confidence is not None:

#             st.metric(
#                 "Confidence",
#                 f"{confidence:.2f}",
#             )

#         else:

#             st.metric(
#                 "Confidence",
#                 "N/A",
#             )

#     # -----------------------------------------------------
#     # Complexity Reasons
#     # -----------------------------------------------------

#     complexity_reasons = result.get(
#         "complexity_reasons",
#         [],
#     )

#     if complexity_reasons:

#         with st.expander(
#             "Complexity Reasons"
#         ):

#             for reason in complexity_reasons:
#                 st.write(f"• {reason}")

#     # -----------------------------------------------------
#     # Escalation Reason
#     # -----------------------------------------------------

#     escalation_reason = result.get(
#         "escalation_reason",
#         "",
#     )

#     if escalation_reason:

#         st.info(
#             f"Escalation / Routing Reason: {escalation_reason}"
#         )

#     # =====================================================
#     # Token Usage
#     # =====================================================

#     st.markdown("### Token Usage")

#     col1, col2 = st.columns(2)

#     with col1:

#         st.metric(
#             "Input Tokens",
#             f"{result.get('input_tokens', 0):,}",
#         )

#     with col2:

#         st.metric(
#             "Output Tokens",
#             f"{result.get('output_tokens', 0):,}",
#         )

#     # =====================================================
#     # Cost Analysis
#     # =====================================================

#     st.markdown("### Cost Analysis")

#     col1, col2, col3 = st.columns(3)

#     actual_cost = result.get(
#         "actual_cost",
#         0.0,
#     )

#     baseline_cost = result.get(
#         "sonnet_baseline_cost",
#         0.0,
#     )

#     savings = result.get(
#         "savings",
#         0.0,
#     )

#     with col1:

#         st.metric(
#             "Actual Cost",
#             f"${actual_cost:.8f}",
#         )

#     with col2:

#         st.metric(
#             "Strong Model Baseline",
#             f"${baseline_cost:.8f}",
#         )

#     with col3:

#         st.metric(
#             "Savings",
#             f"${savings:.8f}",
#         )

#     # -----------------------------------------------------
#     # Savings Percentage
#     # -----------------------------------------------------

#     savings_percentage = result.get(
#         "savings_percentage",
#         0.0,
#     )

#     st.metric(
#         "Savings Percentage",
#         f"{savings_percentage:.2f}%",
#     )



from pathlib import Path

import pandas as pd
import streamlit as st

from prompt_builder import build_prompt
from router import route_request


# =========================================================
# Page Configuration
# =========================================================

st.set_page_config(
    page_title="Cost-Aware Multi-Model Router",
    page_icon="🤖",
    layout="wide",
)


# =========================================================
# Constants
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

LOG_FILE = (
    BASE_DIR
    / "data"
    / "routing_logs.csv"
)

EXPECTED_COLUMNS = [
    "request_id",
    "timestamp",
    "task_type",
    "input_length",
    "complexity_score",
    "complexity_reasons",
    "initial_model",
    "final_model",
    "haiku_confidence",
    "escalated",
    "escalation_reason",
    "input_tokens",
    "output_tokens",
    "actual_cost",
    "sonnet_baseline_cost",
    "savings",
    "savings_percentage",
]


# =========================================================
# Dashboard Data Functions
# =========================================================

def load_routing_logs() -> pd.DataFrame:
    """
    Load routing logs from the CSV file.

    Returns an empty DataFrame if:
    - the file does not exist
    - the file is empty
    - the CSV cannot be read
    - required columns are missing
    """

    if not LOG_FILE.exists():
        return pd.DataFrame(
            columns=EXPECTED_COLUMNS
        )

    try:
        if LOG_FILE.stat().st_size == 0:
            return pd.DataFrame(
                columns=EXPECTED_COLUMNS
            )

        df = pd.read_csv(LOG_FILE)

    except (
        OSError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
    ):
        return pd.DataFrame(
            columns=EXPECTED_COLUMNS
        )

    missing_columns = [
        column
        for column in EXPECTED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        return pd.DataFrame(
            columns=EXPECTED_COLUMNS
        )

    return df


def prepare_dashboard_data(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Clean and prepare routing log data for dashboard metrics.
    """

    if df.empty:
        return df.copy()

    df = df.copy()

    # -----------------------------------------------------
    # Numeric columns
    # -----------------------------------------------------

    numeric_columns = [
        "complexity_score",
        "haiku_confidence",
        "input_tokens",
        "output_tokens",
        "actual_cost",
        "sonnet_baseline_cost",
        "savings",
        "savings_percentage",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # -----------------------------------------------------
    # Boolean column
    # -----------------------------------------------------

    df["escalated"] = (
        df["escalated"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
                "1": True,
                "0": False,
            }
        )
        .fillna(False)
    )

    # -----------------------------------------------------
    # Timestamp
    # -----------------------------------------------------

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
    )

    df = df.sort_values(
        by="timestamp",
        ascending=True,
    )

    # -----------------------------------------------------
    # Cumulative savings
    # -----------------------------------------------------

    df["cumulative_savings"] = (
        df["savings"]
        .fillna(0)
        .cumsum()
    )

    return df


# =========================================================
# Dashboard Metrics
# =========================================================

def calculate_dashboard_metrics(
    df: pd.DataFrame,
) -> dict:
    """
    Calculate KPI values for the dashboard.
    """

    if df.empty:
        return {
            "total_requests": 0,
            "fast_requests": 0,
            "strong_requests": 0,
            "escalation_rate": 0.0,
            "cumulative_savings": 0.0,
            "average_cost": 0.0,
        }

    total_requests = len(df)

    fast_requests = (
        df["final_model"]
        .astype(str)
        .str.contains(
            "deepseek",
            case=False,
            na=False,
        )
        .sum()
    )

    strong_requests = (
        df["final_model"]
        .astype(str)
        .str.contains(
            "gpt",
            case=False,
            na=False,
        )
        .sum()
    )

    escalation_rate = (
        df["escalated"].sum()
        / total_requests
        * 100
    )

    cumulative_savings = (
        df["savings"]
        .fillna(0)
        .sum()
    )

    average_cost = (
        df["actual_cost"]
        .fillna(0)
        .mean()
    )

    return {
        "total_requests": total_requests,
        "fast_requests": int(fast_requests),
        "strong_requests": int(strong_requests),
        "escalation_rate": escalation_rate,
        "cumulative_savings": cumulative_savings,
        "average_cost": average_cost,
    }


# =========================================================
# Request UI
# =========================================================

def render_request_tab():
    """
    Render the request execution interface.
    """

    st.header("Run Request")

    # -----------------------------------------------------
    # Task Type
    # -----------------------------------------------------

    task_type_display = st.selectbox(
        "Task Type",
        [
            "Classification",
            "Extraction",
            "Summarisation",
            "Q&A",
        ],
    )

    task_type_map = {
        "Classification": "classification",
        "Extraction": "extraction",
        "Summarisation": "summarisation",
        "Q&A": "qa",
    }

    task_type = task_type_map[
        task_type_display
    ]

    # -----------------------------------------------------
    # Initialize inputs
    # -----------------------------------------------------

    input_text = ""

    categories = None
    fields = None
    question = None

    # -----------------------------------------------------
    # Classification
    # -----------------------------------------------------

    if task_type == "classification":

        input_text = st.text_area(
            "Input",
            height=250,
            placeholder=(
                "Enter the text you want to classify..."
            ),
        )

        categories_text = st.text_input(
            "Allowed Categories",
            placeholder=(
                "Example: billing, technical, account, general"
            ),
        )

        if categories_text.strip():

            categories = [
                category.strip()
                for category in categories_text.split(",")
                if category.strip()
            ]

    # -----------------------------------------------------
    # Extraction
    # -----------------------------------------------------

    elif task_type == "extraction":

        input_text = st.text_area(
            "Text",
            height=300,
            placeholder=(
                "Enter the text from which you want "
                "to extract information..."
            ),
        )

        fields_text = st.text_input(
            "Fields to Extract",
            placeholder=(
                "Example: name, email, phone"
            ),
        )

        if fields_text.strip():

            fields = [
                field.strip()
                for field in fields_text.split(",")
                if field.strip()
            ]

    # -----------------------------------------------------
    # Summarisation
    # -----------------------------------------------------

    elif task_type == "summarisation":

        input_text = st.text_area(
            "Text to Summarise",
            height=350,
            placeholder=(
                "Enter the text you want to summarise..."
            ),
        )

    # -----------------------------------------------------
    # Q&A
    # -----------------------------------------------------

    elif task_type == "qa":

        input_text = st.text_area(
            "Context",
            height=300,
            placeholder=(
                "Enter the context that should be used "
                "to answer the question..."
            ),
        )

        question = st.text_input(
            "Question",
            placeholder="Enter your question...",
        )

    st.divider()

    # -----------------------------------------------------
    # Run Request
    # -----------------------------------------------------

    run_request = st.button(
        "Run Request",
        type="primary",
        use_container_width=True,
    )

    if not run_request:
        return

    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    if not input_text.strip():

        st.error(
            "Please enter some input before running the request."
        )

        return

    if task_type == "classification" and not categories:

        st.error(
            "Please provide at least one classification category."
        )

        return

    if task_type == "extraction" and not fields:

        st.error(
            "Please provide at least one extraction field."
        )

        return

    if task_type == "qa" and (
        not question
        or not question.strip()
    ):

        st.error(
            "Please enter a question."
        )

        return

    # -----------------------------------------------------
    # Build Prompt
    # -----------------------------------------------------

    try:

        prompt = build_prompt(
            task_type=task_type,
            input_text=input_text,
            categories=categories,
            fields=fields,
            question=question,
        )

    except ValueError as error:

        st.error(
            f"Unable to build request: {error}"
        )

        return

    # -----------------------------------------------------
    # Execute Router
    # -----------------------------------------------------

    try:

        with st.spinner(
            "Analyzing request and selecting the appropriate model..."
        ):

            result = route_request(
                text=prompt,
                task_type=task_type,
            )

    except Exception as error:

        st.error(
            "The request could not be completed."
        )

        st.error(
            str(error)
        )

        return

    # -----------------------------------------------------
    # Result
    # -----------------------------------------------------

    st.divider()

    st.header("Result")

    answer = result.get(
        "answer",
        "",
    )

    st.markdown("### Final Answer")

    if answer:

        st.success(answer)

    else:

        st.warning(
            "No final answer was returned."
        )

    # =====================================================
    # Model Routing
    # =====================================================

    st.markdown("### Model Routing")

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Initial Model",
            result.get(
                "initial_model",
                "N/A",
            ),
        )

    with col2:

        st.metric(
            "Final Model",
            result.get(
                "final_model",
                "N/A",
            ),
        )

    with col3:

        escalated = result.get(
            "escalated",
            False,
        )

        st.metric(
            "Escalated",
            "Yes" if escalated else "No",
        )

    # =====================================================
    # Routing Analysis
    # =====================================================

    st.markdown("### Routing Analysis")

    col1, col2 = st.columns(2)

    with col1:

        complexity_score = result.get(
            "complexity_score",
            0.0,
        )

        st.metric(
            "Complexity Score",
            f"{complexity_score:.2f}",
        )

    with col2:

        confidence = result.get(
            "confidence",
            None,
        )

        if confidence is not None:

            st.metric(
                "Confidence",
                f"{confidence:.2f}",
            )

        else:

            st.metric(
                "Confidence",
                "N/A",
            )

    complexity_reasons = result.get(
        "complexity_reasons",
        [],
    )

    if complexity_reasons:

        with st.expander(
            "Complexity Reasons"
        ):

            for reason in complexity_reasons:

                st.write(
                    f"• {reason}"
                )

    escalation_reason = result.get(
        "escalation_reason",
        "",
    )

    if escalation_reason:

        st.info(
            f"Routing Reason: {escalation_reason}"
        )

    # =====================================================
    # Token Usage
    # =====================================================

    st.markdown("### Token Usage")

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Input Tokens",
            f"{result.get('input_tokens', 0):,}",
        )

    with col2:

        st.metric(
            "Output Tokens",
            f"{result.get('output_tokens', 0):,}",
        )

    # =====================================================
    # Cost Analysis
    # =====================================================

    st.markdown("### Cost Analysis")

    col1, col2, col3 = st.columns(3)

    actual_cost = result.get(
        "actual_cost",
        0.0,
    )

    baseline_cost = result.get(
        "sonnet_baseline_cost",
        0.0,
    )

    savings = result.get(
        "savings",
        0.0,
    )

    with col1:

        st.metric(
            "Actual Cost",
            f"${actual_cost:.8f}",
        )

    with col2:

        st.metric(
            "Strong Model Baseline",
            f"${baseline_cost:.8f}",
        )

    with col3:

        st.metric(
            "Savings",
            f"${savings:.8f}",
        )

    savings_percentage = result.get(
        "savings_percentage",
        0.0,
    )

    st.metric(
        "Savings Percentage",
        f"{savings_percentage:.2f}%",
    )


# =========================================================
# Dashboard
# =========================================================

def render_dashboard_tab():
    """
    Render analytics dashboard.
    """

    st.header("Analytics Dashboard")

    df = load_routing_logs()

    if df.empty:

        st.info(
            "No routing requests have been logged yet. "
            "Run a request from the 'Run Request' tab "
            "to populate the dashboard."
        )

        return

    df = prepare_dashboard_data(df)

    metrics = calculate_dashboard_metrics(df)

    # =====================================================
    # KPI Cards
    # =====================================================

    st.subheader("Key Performance Indicators")

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Total Requests",
            f"{metrics['total_requests']:,}",
        )

    with col2:

        st.metric(
            "Fast Model Requests",
            f"{metrics['fast_requests']:,}",
        )

    with col3:

        st.metric(
            "Strong Model Requests",
            f"{metrics['strong_requests']:,}",
        )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Escalation Rate",
            f"{metrics['escalation_rate']:.2f}%",
        )

    with col2:

        st.metric(
            "Cumulative Savings",
            f"${metrics['cumulative_savings']:.8f}",
        )

    with col3:

        st.metric(
            "Average Cost / Request",
            f"${metrics['average_cost']:.8f}",
        )

    st.divider()

    # =====================================================
    # Chart 1: Fast vs Strong Usage
    # =====================================================

    st.subheader(
        "1. Fast vs Strong Model Usage"
    )

    usage_data = pd.DataFrame(
        {
            "Model": [
                "Fast Model",
                "Strong Model",
            ],
            "Requests": [
                metrics["fast_requests"],
                metrics["strong_requests"],
            ],
        }
    )

    st.bar_chart(
        usage_data.set_index("Model")
    )

    # =====================================================
    # Chart 2: Cost Comparison
    # =====================================================

    st.subheader(
        "2. Cost Comparison"
    )

    router_cost = (
        df["actual_cost"]
        .fillna(0)
        .sum()
    )

    strong_baseline_cost = (
        df["sonnet_baseline_cost"]
        .fillna(0)
        .sum()
    )

    cost_data = pd.DataFrame(
        {
            "Strategy": [
                "Always Strong Model",
                "Cost-Aware Router",
            ],
            "Cost": [
                strong_baseline_cost,
                router_cost,
            ],
        }
    )

    st.bar_chart(
        cost_data.set_index("Strategy")
    )

    st.caption(
        "The Always Strong Model value is the estimated "
        "strong-model baseline stored for each request."
    )

    # =====================================================
    # Chart 3: Savings Over Time
    # =====================================================

    st.subheader(
        "3. Savings Over Time"
    )

    savings_data = df[
        [
            "timestamp",
            "cumulative_savings",
        ]
    ].dropna(
        subset=["timestamp"]
    )

    if not savings_data.empty:

        savings_data = savings_data.set_index(
            "timestamp"
        )

        st.line_chart(
            savings_data[
                "cumulative_savings"
            ]
        )

    else:

        st.info(
            "No valid timestamps are available for the "
            "savings chart."
        )

    # =====================================================
    # Chart 4: Requests by Task Type
    # =====================================================

    st.subheader(
        "4. Requests by Task Type"
    )

    task_counts = (
        df["task_type"]
        .fillna("unknown")
        .value_counts()
        .rename("Requests")
    )

    st.bar_chart(
        task_counts
    )

    # =====================================================
    # Routing History
    # =====================================================

    st.subheader(
        "Routing History"
    )

    history_columns = [
        "timestamp",
        "task_type",
        "initial_model",
        "final_model",
        "haiku_confidence",
        "escalated",
        "actual_cost",
        "savings",
        "escalation_reason",
    ]

    history = df[
        history_columns
    ].copy()

    history = history.sort_values(
        by="timestamp",
        ascending=False,
    )

    history = history.rename(
        columns={
            "haiku_confidence": "confidence",
        }
    )

    st.dataframe(
        history,
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# Main Application
# =========================================================

st.title(
    "Cost-Aware Multi-Model Router"
)

st.subheader(
    "Route every request to the cheapest model that can actually handle it."
)

st.divider()


# =========================================================
# Tabs
# =========================================================

run_tab, dashboard_tab = st.tabs(
    [
        "Run Request",
        "Dashboard",
    ]
)


with run_tab:

    render_request_tab()


with dashboard_tab:

    render_dashboard_tab()