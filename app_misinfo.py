import os
import json
import glob
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Cancer Misinformation Annotation", layout="wide")

# -----------------------------
# Config
# -----------------------------
DATA_DIR = st.sidebar.text_input(
    "Folder path containing JSON files",
    value="data/misinformation_results"  # <-- change this to your folder
)

OUTPUT_PATH = st.sidebar.text_input(
    "Where to save annotations (CSV)",
    value="misinformation_annotations_expert.csv"
)

# -----------------------------
# Helpers
# -----------------------------
def load_json_files(data_dir: str) -> pd.DataFrame:
    """Load all .json files in a folder; extract 'body' and keep full raw JSON."""
    paths = sorted(glob.glob(os.path.join(data_dir, "*.json")))
    rows = []
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8") as f:
                obj = json.load(f)
            body = obj.get("body", "")
            rows.append({
                "file_path": p,
                "file_name": os.path.basename(p),
                "body": body if body is not None else "",
                "raw": obj,  # keep whole json in case you want ids later
            })
        except Exception as e:
            rows.append({
                "file_path": p,
                "file_name": os.path.basename(p),
                "body": "",
                "raw": {"_load_error": str(e)},
            })
    return pd.DataFrame(rows)

def load_existing_annotations(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def append_annotation(path: str, record: dict) -> None:
    """Append one annotation row to CSV; create file with headers if missing."""
    df_row = pd.DataFrame([record])
    if os.path.exists(path):
        df_row.to_csv(path, mode="a", header=False, index=False)
    else:
        df_row.to_csv(path, mode="w", header=True, index=False)

# -----------------------------
# Load data
# -----------------------------
if not DATA_DIR or not os.path.isdir(DATA_DIR):
    st.error("Please enter a valid folder path that exists on this machine.")
    st.stop()

data_df = load_json_files(DATA_DIR)
st.sidebar.write(f"Loaded files: **{len(data_df)}**")

existing_df = load_existing_annotations(OUTPUT_PATH)

# Determine which files are already annotated
annotated_files = set(existing_df["file_name"].astype(str).tolist()) if not existing_df.empty and "file_name" in existing_df.columns else set()
data_df["is_annotated"] = data_df["file_name"].astype(str).isin(annotated_files)

# Filter
show_mode = st.sidebar.radio(
    "Show",
    ["Unannotated only", "All"],
    index=0,
    horizontal=False
)

if show_mode == "Unannotated only":
    work_df = data_df[~data_df["is_annotated"]].reset_index(drop=True)
else:
    work_df = data_df.reset_index(drop=True)

if work_df.empty:
    st.success("No items to annotate 🎉 (based on your current output file).")
    st.stop()

# -----------------------------
# Session state
# -----------------------------
if "idx" not in st.session_state:
    st.session_state.idx = 0

# Clamp idx in case the filter changes
st.session_state.idx = max(0, min(st.session_state.idx, len(work_df) - 1))

row = work_df.iloc[st.session_state.idx]

# -----------------------------
# UI
# -----------------------------
colA, colB, colC = st.columns([2, 1, 1])
with colA:
    st.title("Cancer Misinformation Annotation")
    st.caption(f"File: {row['file_name']}  |  {st.session_state.idx+1} / {len(work_df)}")
with colB:
    st.metric("Total", len(data_df))
with colC:
    st.metric("Remaining", int((~data_df["is_annotated"]).sum()))

st.divider()

body_text = row["body"]
if not isinstance(body_text, str):
    body_text = "" if body_text is None else str(body_text)

st.subheader("Text to annotate")
st.write(body_text if body_text.strip() else "_(Empty body)_")

st.divider()

# Annotation tasks
misinformation = st.radio(
    "1) Is this misinformation?",
    ["Misinformation", "Not misinformation", "Unclear"],
    horizontal=True,
    index=2
)

info_behavior = st.radio(
    "2) Information behavior",
    ["Seeking", "Sharing", "Neither"],
    horizontal=True,
    index=2
)

cancer_stage = st.radio(
    "3) Cancer stage",
    ["Screening", "Treatment", "Unclear or Neither"],
    horizontal=True,
    index=2
)

risk_level = st.radio(
    "4) Risk Level",
    ["Low-Risk", "Moderate-Risk", "High-Risk"],
    horizontal=True,
    index=2
)

misinfo_kind = st.radio(
    "5) Kind of misinformation",
    ["Satire or Pardoy", "False Connection", "Misleading Content", "False Context", "Imposter Content", "Fabricated Content"],
    horizontal=True,
    index=5
)


notes = st.text_input("Optional notes (for yourself)", value="")

# Navigation / save buttons
c1, c2, c3, c4 = st.columns([1, 1, 1, 2])

with c1:
    if st.button("⬅️ Prev", use_container_width=True, disabled=(st.session_state.idx == 0)):
        st.session_state.idx -= 1
        st.rerun()

with c2:
    if st.button("Next ➡️", use_container_width=True):
        st.session_state.idx = min(st.session_state.idx + 1, len(work_df) - 1)
        st.rerun()

with c3:
    if st.button("Save ✅", use_container_width=True):
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "file_name": row["file_name"],
            "file_path": row["file_path"],
            "misinformation": misinformation,
            "info_behavior": info_behavior,
            "notes": notes,
        }
        append_annotation(OUTPUT_PATH, record)
        st.success("Saved.")

        # Move forward (and rerun so it disappears from "Unannotated only")
        st.session_state.idx = min(st.session_state.idx + 1, len(work_df) - 1)
        st.rerun()

with c4:
    st.caption(f"Saving to: `{OUTPUT_PATH}`")

# Optional: show raw JSON (debug)
with st.expander("Show raw JSON (debug)", expanded=False):
    st.json(row["raw"])
