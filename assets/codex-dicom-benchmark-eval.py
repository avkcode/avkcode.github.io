#!/usr/bin/env python3
"""
Run the public DICOM benchmark used in the blog post.

Providers:
  - codex: existing single-pass Codex CLI flow
  - openai: OpenAI Responses API with three benchmark modes and a seeing->explaining split

Requirements:
  - Python packages: numpy, pillow, pydicom
  - For provider=codex: Codex CLI installed and authenticated
  - For provider=openai: OPENAI_API_KEY set

Examples:
  python3 codex-dicom-benchmark-eval.py \
    --provider codex \
    --output-dir /tmp/codex-benchmark \
    --model gpt-5.4

  python3 codex-dicom-benchmark-eval.py \
    --provider openai \
    --output-dir /tmp/openai-benchmark \
    --seeing-model gpt-5.4 \
    --explaining-model gpt-5.4-mini \
    --benchmark-modes image-only,image+metadata,image+metadata+roi
"""

from __future__ import annotations

import argparse
import base64
import gzip
import html
import json
import math
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Any

CASES = [
    {
        "id": "appendicitis",
        "title": "CASE 1: Acute appendicitis",
        "case_url": "https://www.pacsbin.com/c/ZyenvVwTS4",
        "expected_diagnosis": "acute appendicitis",
        "modality": "CT",
        "selected_link_index": 0,
        "selected_key_text": "dilated, fluid filled appendix",
        "match_regex": r"appendicitis",
    },
    {
        "id": "pulmonary_embolism",
        "title": "Case 14: Acute pulmonary embolism",
        "case_url": "https://www.pacsbin.com/c/ZywILUuaFq",
        "expected_diagnosis": "acute pulmonary embolism",
        "modality": "CT angiography",
        "selected_link_index": 1,
        "selected_key_text": "segmental left upper lobe pulmonary artery embolus",
        "match_regex": r"pulmonary embol|pulmonary embolus|\bpe\b",
    },
    {
        "id": "perforated_sigmoid_diverticulitis",
        "title": "Perforated sigmoid diverticulitis",
        "case_url": "https://www.pacsbin.com/c/bkbnW8-OEV",
        "expected_diagnosis": "perforated sigmoid diverticulitis",
        "modality": "CT",
        "selected_link_index": 1,
        "selected_key_text": "locules of free air adjacent to sigmoid colon",
        "match_regex": r"perforat.*diverticulitis|diverticulitis.*perforat",
        "partial_regex": r"diverticulitis",
    },
    {
        "id": "cecal_diverticulitis",
        "title": "CT Abdomen and Pelvis - Cecal diverticulitis",
        "case_url": "https://www.pacsbin.com/c/WJShjjiUBu",
        "expected_diagnosis": "cecal diverticulitis",
        "modality": "CT",
        "selected_link_index": 0,
        "selected_key_text": "inflammatory stranding adjacent to cecal diverticulum",
        "match_regex": r"diverticulitis",
    },
    {
        "id": "sigmoid_diverticulitis",
        "title": "Sigmoid diverticulitis",
        "case_url": "https://www.pacsbin.com/c/WJ_W6lt3KN",
        "expected_diagnosis": "sigmoid diverticulitis",
        "modality": "CT",
        "selected_link_index": 0,
        "selected_key_text": "inflamed sigmoid diverticulum",
        "match_regex": r"diverticulitis",
    },
    {
        "id": "strangulated_hernia_small_bowel_ischemia",
        "title": "Strangulated hernia with small bowel ischemia",
        "case_url": "https://www.pacsbin.com/c/Zy71Y8Y99c",
        "expected_diagnosis": "hernia complicated by small bowel ischemia (strangulation)",
        "modality": "CT",
        "selected_link_index": 2,
        "selected_key_text": "hypoenhancing small bowel loops in the hernia sac",
        "match_regex": r"strangulat|small[- ]?bowel ischem|ischemic bowel|bowel ischem",
        "partial_regex": r"hernia|obstruction",
    },
    {
        "id": "perforated_appendicitis",
        "title": "Perforated appendicitis",
        "case_url": "https://www.pacsbin.com/c/-kmjPQmoDr",
        "expected_diagnosis": "perforated appendicitis",
        "modality": "CT",
        "selected_link_index": 2,
        "selected_key_text": "mucosal discontinuity with extraluminal air and fluid",
        "match_regex": r"perforat.*appendicitis|appendicitis.*perforat",
        "partial_regex": r"appendicitis",
    },
    {
        "id": "appendicitis_in_pregnancy",
        "title": "Appendicitis in pregnancy",
        "case_url": "https://www.pacsbin.com/c/WyWoKcFKUU",
        "expected_diagnosis": "acute uncomplicated appendicitis in pregnancy",
        "modality": "MRI",
        "selected_link_index": 0,
        "selected_key_text": "appendiceal lumen distended to >6 mm with T2-hyperintense contents",
        "match_regex": r"appendicitis",
    },
    {
        "id": "left_mca_infarction",
        "title": "Acute left MCA infarction",
        "case_url": "https://www.pacsbin.com/c/WkUP_QRFD8",
        "expected_diagnosis": "acute left multifocal MCA distribution ischemia/infarction",
        "modality": "MRI",
        "selected_link_index": 0,
        "selected_key_text": "patchy left multifocal MCA distribution diffusion restriction",
        "match_regex": r"(mca.*infar|infar.*mca|acute ischemic stroke|acute stroke|acute infarct)",
        "partial_regex": r"infar|ischemi|stroke",
    },
    {
        "id": "cauda_equina_compression",
        "title": "Cauda equina compression from severe stenosis",
        "case_url": "https://www.pacsbin.com/c/WySaY7RFDU",
        "expected_diagnosis": "severe central stenosis with compression of the cauda equina at multiple levels",
        "modality": "MRI",
        "selected_link_index": 0,
        "selected_key_text": "severe L3-4 and L4-5 central stenosis with compression of the cauda equina",
        "match_regex": r"cauda equina|central stenosis",
        "partial_regex": r"stenosis|compression",
    },
]

DEFAULT_OPENAI_MODES = ("image-only", "image+metadata", "image+metadata+roi")

CODEX_PROMPT_TEMPLATE = """You are evaluating a single de-identified DICOM teaching-case slice for research only, not clinical care.
Return only the structured schema.
Use the attached image as primary evidence and the metadata only as supporting context.
Be specific about the single most likely diagnosis visible on this slice.

Metadata:
{metadata}
"""

SEEING_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "candidate_diagnosis",
        "confidence",
        "primary_visual_finding",
        "attention_target",
        "supporting_visual_evidence",
        "candidate_differentials",
        "counter_evidence",
        "uncertainties",
    ],
    "properties": {
        "candidate_diagnosis": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "primary_visual_finding": {"type": "string"},
        "attention_target": {"type": "string"},
        "supporting_visual_evidence": {"type": "array", "items": {"type": "string"}},
        "candidate_differentials": {"type": "array", "items": {"type": "string"}},
        "counter_evidence": {"type": "array", "items": {"type": "string"}},
        "uncertainties": {"type": "array", "items": {"type": "string"}},
    },
}

EXPLAINING_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "diagnosis",
        "confidence",
        "final_claim",
        "counter_evidence",
        "manual_verification_steps",
        "draft_findings",
        "draft_impression",
    ],
    "properties": {
        "diagnosis": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "final_claim": {"type": "string"},
        "counter_evidence": {"type": "array", "items": {"type": "string"}},
        "manual_verification_steps": {"type": "array", "items": {"type": "string"}},
        "draft_findings": {"type": "string"},
        "draft_impression": {"type": "string"},
    },
}

CODEX_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["diagnosis", "confidence", "visible_findings", "reasoning", "uncertainties"],
    "properties": {
        "diagnosis": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "visible_findings": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
        "uncertainties": {"type": "array", "items": {"type": "string"}},
    },
}


class AutoScrollLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "") or ""
        if "auto-scroll" in classes.split():
            self._current_href = html.unescape(attrs_dict.get("href", "") or "")
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current_href is None:
            return
        text = " ".join(" ".join(self._current_text).split())
        self.links.append({"href": self._current_href, "text": text})
        self._current_href = None
        self._current_text = []


@dataclass
class ResolvedCase:
    case: dict[str, Any]
    studydata: dict[str, Any]
    key_link_href: str
    key_link_text: str
    series: dict[str, Any]
    instance: dict[str, Any]
    window_center: float | None
    window_width: float | None


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "codex-dicom-benchmark/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def fetch_text(url: str) -> str:
    return fetch_bytes(url).decode("utf-8", errors="replace")


def extract_studydata(page_html: str) -> dict[str, Any]:
    marker = "var studydata = "
    start = page_html.find(marker)
    if start == -1:
        raise ValueError("Could not find studydata marker in page")

    brace_start = page_html.find("{", start)
    if brace_start == -1:
        raise ValueError("Could not find studydata object start in page")

    depth = 0
    in_string = False
    escaped = False
    for index in range(brace_start, len(page_html)):
        char = page_html[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(page_html[brace_start : index + 1])

    raise ValueError("Could not find end of studydata object in page")


def extract_auto_scroll_links(notes_html: str) -> list[dict[str, str]]:
    parser = AutoScrollLinkParser()
    parser.feed(notes_html)
    return parser.links


def resolve_case(case: dict[str, Any]) -> ResolvedCase:
    page_html = fetch_text(case["case_url"])
    studydata = extract_studydata(page_html)
    links = extract_auto_scroll_links(studydata["notes"])
    selected_link = links[case["selected_link_index"]]

    query = urllib.parse.parse_qs(urllib.parse.urlparse(selected_link["href"]).query)
    series_id = query["s"][0]
    instance_id = query["i"][0]
    window_width = float(query["ww"][0]) if "ww" in query else None
    window_center = float(query["wc"][0]) if "wc" in query else None

    series = next(item for item in studydata["series"] if item["_id"] == series_id)
    instance = next(item for item in series["instances"] if item["_id"] == instance_id)

    return ResolvedCase(
        case=case,
        studydata=studydata,
        key_link_href=selected_link["href"],
        key_link_text=selected_link["text"],
        series=series,
        instance=instance,
        window_center=window_center,
        window_width=window_width,
    )


def render_dicom_png(dicom_bytes: bytes, png_path: Path, wc: float | None, ww: float | None) -> Any:
    import numpy as np
    import pydicom
    from PIL import Image

    ds = pydicom.dcmread(BytesIO(dicom_bytes), force=True)
    pixels = ds.pixel_array.astype(np.float32)

    if pixels.ndim > 2 and pixels.shape[-1] in (3, 4):
        image = Image.fromarray(pixels.astype(np.uint8))
        image.save(png_path)
        return ds

    if pixels.ndim > 2:
        pixels = pixels[0]

    slope = float(getattr(ds, "RescaleSlope", 1) or 1)
    intercept = float(getattr(ds, "RescaleIntercept", 0) or 0)
    pixels = pixels * slope + intercept

    if wc is None or ww is None:
        if getattr(ds, "WindowCenter", None) is not None and getattr(ds, "WindowWidth", None) is not None:
            wc = float(np.ravel(ds.WindowCenter)[0])
            ww = float(np.ravel(ds.WindowWidth)[0])
        else:
            low = float(np.percentile(pixels, 0.5))
            high = float(np.percentile(pixels, 99.5))
            wc = (low + high) / 2.0
            ww = max(high - low, 1.0)

    low = wc - ww / 2.0
    high = wc + ww / 2.0
    scaled = np.clip((pixels - low) / max(high - low, 1e-6), 0.0, 1.0)

    if str(getattr(ds, "PhotometricInterpretation", "")).upper() == "MONOCHROME1":
        scaled = 1.0 - scaled

    image = Image.fromarray((scaled * 255).astype(np.uint8), mode="L")
    image.save(png_path)
    return ds


def metadata_summary(case: dict[str, Any], studydata: dict[str, Any], series: dict[str, Any], ds: Any) -> str:
    rows = [
        f"Published modality bucket: {case['modality']}",
        f"Series label: {series.get('label', '')}",
        f"Series modality: {series.get('modality', '')}",
        f"Study description: {ds.get('StudyDescription', '')}",
        f"Series description: {ds.get('SeriesDescription', '')}",
        f"Body part examined: {ds.get('BodyPartExamined', '')}",
        f"Image dimensions: {ds.get('Rows', '')} x {ds.get('Columns', '')}",
    ]
    return "\n".join(row for row in rows if not row.endswith(": "))


def encode_image_data_url(image_path: Path) -> str:
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _collect_annotation_points(value: Any, points: list[tuple[float, float]], path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        if {"x", "y"}.issubset(value.keys()):
            skip = {"textBox", "boundingBox"} & set(path)
            if not skip:
                x = value.get("x")
                y = value.get("y")
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    points.append((float(x), float(y)))
        for key, nested in value.items():
            _collect_annotation_points(nested, points, path + (str(key),))
    elif isinstance(value, list):
        for item in value:
            _collect_annotation_points(item, points, path)


def extract_annotation_bbox(instance: dict[str, Any], width: int, height: int) -> dict[str, Any] | None:
    annotations = instance.get("annotations")
    if not isinstance(annotations, dict):
        return None

    points: list[tuple[float, float]] = []
    _collect_annotation_points(annotations, points)
    if not points:
        return None

    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    x1, x2 = min(xs), max(xs)
    y1, y2 = min(ys), max(ys)
    pad_x = max(24.0, (x2 - x1) * 0.45)
    pad_y = max(24.0, (y2 - y1) * 0.45)

    left = max(0, int(math.floor(x1 - pad_x)))
    top = max(0, int(math.floor(y1 - pad_y)))
    right = min(width, int(math.ceil(x2 + pad_x)))
    bottom = min(height, int(math.ceil(y2 + pad_y)))

    if right <= left or bottom <= top:
        return None

    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": right - left,
        "height": bottom - top,
        "source": "instance_annotations",
        "point_count": len(points),
    }


def crop_roi(full_image_path: Path, roi_path: Path, bbox: dict[str, Any] | None) -> dict[str, Any] | None:
    from PIL import Image

    if bbox is None:
        return None
    image = Image.open(full_image_path)
    crop = image.crop((bbox["left"], bbox["top"], bbox["right"], bbox["bottom"]))
    crop.save(roi_path)
    return bbox


def run_codex(model: str, png_path: Path, prompt: str, schema_path: Path, output_path: Path) -> dict[str, Any]:
    cmd = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--model",
        model,
        "--image",
        str(png_path),
        "--output-schema",
        str(schema_path),
        "--output-last-message",
        str(output_path),
        "-",
    ]
    proc = subprocess.run(cmd, input=prompt, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"codex exec failed\nstdout:\n{proc.stdout}\n\nstderr:\n{proc.stderr}")
    return json.loads(output_path.read_text())


def openai_extract_output_text(body: dict[str, Any]) -> str:
    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    chunks: list[str] = []
    for item in body.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str):
                    chunks.append(text)
    if chunks:
        return "".join(chunks)
    raise ValueError(f"Could not extract output text from OpenAI response: {json.dumps(body)[:1200]}")


def run_openai_responses(
    api_key: str,
    api_base: str,
    model: str,
    schema_name: str,
    schema: dict[str, Any],
    messages: list[dict[str, Any]],
    output_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = {
        "model": model,
        "input": messages,
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema,
            }
        },
    }
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_text = exc.read().decode("utf-8", errors="replace")
        error_path = output_path.with_suffix(output_path.suffix + ".error.json")
        error_path.write_text(error_text + "\n")
        raise RuntimeError(
            f"OpenAI Responses API request failed with HTTP {exc.code} {exc.reason}\n{error_text}"
        ) from exc

    output_path.write_text(json.dumps(body, indent=2) + "\n")
    parsed = json.loads(openai_extract_output_text(body))
    return parsed, body


def score_prediction(case: dict[str, Any], diagnosis: str) -> str:
    diagnosis_l = diagnosis.lower()
    if re.search(case["match_regex"], diagnosis_l):
        return "match"
    partial_regex = case.get("partial_regex")
    if partial_regex and re.search(partial_regex, diagnosis_l):
        return "partial"
    return "miss"


def mode_uses_metadata(mode: str) -> bool:
    return mode in {"image+metadata", "image+metadata+roi"}


def mode_uses_roi(mode: str) -> bool:
    return mode == "image+metadata+roi"


def openai_schema_name(case_id: str, mode: str, stage: str) -> str:
    mode_code = {
        "image-only": "io",
        "image+metadata": "im",
        "image+metadata+roi": "imr",
    }.get(mode, "x")
    stage_code = {"seeing": "see", "explaining": "exp"}.get(stage, stage[:3])
    sanitized_case = re.sub(r"[^a-z0-9]+", "_", case_id.lower()).strip("_")
    sanitized_case = sanitized_case[:40]
    return f"{sanitized_case}_{mode_code}_{stage_code}"


def build_seeing_messages(
    mode: str,
    metadata: str,
    full_data_url: str,
    roi_data_url: str | None,
    detail: str,
) -> list[dict[str, Any]]:
    instructions = [
        "You are the seeing pass for a research-only benchmark over a de-identified single DICOM teaching-case slice.",
        "Work from the pixels first and do not over-trust metadata.",
        "Return only the structured schema.",
        "Name the single most likely diagnosis visible on this slice, but include counter-evidence and alternatives.",
    ]
    if mode_uses_metadata(mode):
        instructions.append("Metadata is available below as supporting context only.")
    else:
        instructions.append("No metadata is provided in this mode.")
    if mode_uses_roi(mode) and roi_data_url is not None:
        instructions.append("You will receive two images: the full slice first, then a crop around the published teaching-point annotation.")

    content: list[dict[str, Any]] = [{"type": "input_text", "text": "\n".join(instructions)}]
    if mode_uses_metadata(mode):
        content.append({"type": "input_text", "text": f"Metadata:\n{metadata}"})
    content.append({"type": "input_image", "image_url": full_data_url, "detail": detail})
    if mode_uses_roi(mode) and roi_data_url is not None:
        content.append({"type": "input_image", "image_url": roi_data_url, "detail": detail})

    return [{"role": "user", "content": content}]


def build_explaining_messages(
    mode: str,
    metadata: str,
    full_data_url: str,
    roi_data_url: str | None,
    detail: str,
    seeing_output: dict[str, Any],
) -> list[dict[str, Any]]:
    instructions = [
        "You are the explaining pass for a research-only benchmark over a de-identified DICOM teaching-case slice.",
        "Use the image as primary evidence and the seeing-pass JSON as a hypothesis to audit, not as ground truth.",
        "Return only the structured schema.",
        "If the seeing pass appears off-target, say so through counter-evidence and verification steps.",
    ]
    if mode_uses_metadata(mode):
        instructions.append("Metadata is available below as secondary context.")
    if mode_uses_roi(mode) and roi_data_url is not None:
        instructions.append("You will receive the full slice plus the ROI crop used in the seeing pass.")

    content: list[dict[str, Any]] = [
        {"type": "input_text", "text": "\n".join(instructions)},
        {"type": "input_text", "text": f"Seeing-pass JSON:\n{json.dumps(seeing_output, indent=2)}"},
    ]
    if mode_uses_metadata(mode):
        content.append({"type": "input_text", "text": f"Metadata:\n{metadata}"})
    content.append({"type": "input_image", "image_url": full_data_url, "detail": detail})
    if mode_uses_roi(mode) and roi_data_url is not None:
        content.append({"type": "input_image", "image_url": roi_data_url, "detail": detail})

    return [{"role": "user", "content": content}]


def confidence_bins(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bins: list[dict[str, Any]] = []
    for start in (0.0, 0.2, 0.4, 0.6, 0.8):
        end = round(start + 0.2, 1)
        bucket = [row for row in results if start <= float(row["confidence"]) < end or (end == 1.0 and float(row["confidence"]) == 1.0)]
        if not bucket:
            bins.append({"range": f"{start:.1f}-{end:.1f}", "count": 0, "avg_confidence": None, "avg_outcome": None})
            continue
        outcomes = [1.0 if row["verdict"] == "match" else 0.5 if row["verdict"] == "partial" else 0.0 for row in bucket]
        bins.append(
            {
                "range": f"{start:.1f}-{end:.1f}",
                "count": len(bucket),
                "avg_confidence": sum(float(row["confidence"]) for row in bucket) / len(bucket),
                "avg_outcome": sum(outcomes) / len(outcomes),
            }
        )
    return bins


def summarize_mode(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {"total_cases": 0, "match": 0, "partial": 0, "miss": 0}
    confidences: dict[str, list[float]] = {"match": [], "partial": [], "miss": []}
    brier_terms: list[float] = []

    for row in results:
        verdict = row["verdict"]
        confidence = float(row["confidence"])
        summary["total_cases"] += 1
        summary[verdict] += 1
        confidences[verdict].append(confidence)
        target = 1.0 if verdict == "match" else 0.5 if verdict == "partial" else 0.0
        brier_terms.append((confidence - target) ** 2)

    return {
        **summary,
        "strict_top1_accuracy": summary["match"] / summary["total_cases"],
        "directionally_useful_accuracy": (summary["match"] + summary["partial"]) / summary["total_cases"],
        "average_confidence_by_verdict": {
            key: (sum(values) / len(values) if values else None) for key, values in confidences.items()
        },
        "brier_score_partial_05": sum(brier_terms) / len(brier_terms),
        "confidence_bins": confidence_bins(results),
    }


def evaluate_case_codex(case: dict[str, Any], output_dir: Path, model: str) -> dict[str, Any]:
    resolved = resolve_case(case)
    case_dir = output_dir / case["id"]
    case_dir.mkdir(parents=True, exist_ok=True)

    dicom_url = resolved.instance["url"]
    dicom_bytes = fetch_bytes(dicom_url)
    if dicom_url.endswith(".gz"):
        dicom_bytes = gzip.decompress(dicom_bytes)

    dicom_path = case_dir / "slice.dcm"
    png_path = case_dir / "slice.png"
    schema_path = case_dir / "schema.json"
    response_path = case_dir / "codex-response.json"

    dicom_path.write_bytes(dicom_bytes)
    ds = render_dicom_png(dicom_bytes, png_path, resolved.window_center, resolved.window_width)
    schema_path.write_text(json.dumps(CODEX_SCHEMA, indent=2) + "\n")

    metadata = metadata_summary(case, resolved.studydata, resolved.series, ds)
    prompt = CODEX_PROMPT_TEMPLATE.format(metadata=metadata)
    model_output = run_codex(model, png_path, prompt, schema_path, response_path)
    verdict = score_prediction(case, model_output["diagnosis"])

    result = {
        "id": case["id"],
        "title": case["title"],
        "case_url": case["case_url"],
        "modality": case["modality"],
        "expected_diagnosis": case["expected_diagnosis"],
        "selected_link_index": case["selected_link_index"],
        "selected_key_text": resolved.key_link_text,
        "selected_link_href": resolved.key_link_href,
        "window_center": resolved.window_center,
        "window_width": resolved.window_width,
        "dicom_url": dicom_url,
        "metadata_summary": metadata,
        "diagnosis": model_output["diagnosis"],
        "confidence": model_output["confidence"],
        "visible_findings": model_output["visible_findings"],
        "reasoning": model_output["reasoning"],
        "uncertainties": model_output["uncertainties"],
        "verdict": verdict,
    }
    (output_dir / f"{case['id']}.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def evaluate_case_openai(
    case: dict[str, Any],
    output_dir: Path,
    api_key: str,
    api_base: str,
    seeing_model: str,
    explaining_model: str,
    benchmark_modes: tuple[str, ...],
    detail: str,
) -> dict[str, Any]:
    resolved = resolve_case(case)
    case_dir = output_dir / case["id"]
    case_dir.mkdir(parents=True, exist_ok=True)

    dicom_url = resolved.instance["url"]
    dicom_bytes = fetch_bytes(dicom_url)
    if dicom_url.endswith(".gz"):
        dicom_bytes = gzip.decompress(dicom_bytes)

    dicom_path = case_dir / "slice.dcm"
    png_path = case_dir / "slice.png"
    roi_path = case_dir / "slice-roi.png"

    dicom_path.write_bytes(dicom_bytes)
    ds = render_dicom_png(dicom_bytes, png_path, resolved.window_center, resolved.window_width)
    metadata = metadata_summary(case, resolved.studydata, resolved.series, ds)

    full_data_url = encode_image_data_url(png_path)
    bbox = extract_annotation_bbox(resolved.instance, int(ds.Columns), int(ds.Rows))
    roi_bbox = crop_roi(png_path, roi_path, bbox)
    roi_data_url = encode_image_data_url(roi_path) if roi_bbox is not None else None

    mode_results: dict[str, Any] = {}
    for mode in benchmark_modes:
        seeing_messages = build_seeing_messages(mode, metadata, full_data_url, roi_data_url, detail)
        seeing_output, seeing_raw = run_openai_responses(
            api_key=api_key,
            api_base=api_base,
            model=seeing_model,
            schema_name=openai_schema_name(case["id"], mode, "seeing"),
            schema=SEEING_SCHEMA,
            messages=seeing_messages,
            output_path=case_dir / f"{mode}-seeing-raw.json",
        )

        explaining_messages = build_explaining_messages(
            mode=mode,
            metadata=metadata,
            full_data_url=full_data_url,
            roi_data_url=roi_data_url,
            detail=detail,
            seeing_output=seeing_output,
        )
        explaining_output, explaining_raw = run_openai_responses(
            api_key=api_key,
            api_base=api_base,
            model=explaining_model,
            schema_name=openai_schema_name(case["id"], mode, "explaining"),
            schema=EXPLAINING_SCHEMA,
            messages=explaining_messages,
            output_path=case_dir / f"{mode}-explaining-raw.json",
        )

        verdict = score_prediction(case, explaining_output["diagnosis"])
        mode_result = {
            "provider": "openai-responses",
            "seeing_model": seeing_model,
            "explaining_model": explaining_model,
            "mode": mode,
            "detail": detail,
            "roi_used": mode_uses_roi(mode) and roi_bbox is not None,
            "roi_bbox": roi_bbox,
            "diagnosis": explaining_output["diagnosis"],
            "confidence": explaining_output["confidence"],
            "visible_findings": seeing_output["supporting_visual_evidence"],
            "reasoning": explaining_output["final_claim"],
            "uncertainties": seeing_output["uncertainties"],
            "counter_evidence": explaining_output["counter_evidence"],
            "manual_verification_steps": explaining_output["manual_verification_steps"],
            "draft_findings": explaining_output["draft_findings"],
            "draft_impression": explaining_output["draft_impression"],
            "seeing_pass": seeing_output,
            "explaining_pass": explaining_output,
            "verdict": verdict,
        }
        (case_dir / f"{mode}.json").write_text(json.dumps(mode_result, indent=2) + "\n")
        mode_results[mode] = mode_result

    case_result = {
        "id": case["id"],
        "title": case["title"],
        "case_url": case["case_url"],
        "modality": case["modality"],
        "expected_diagnosis": case["expected_diagnosis"],
        "selected_link_index": case["selected_link_index"],
        "selected_key_text": resolved.key_link_text,
        "selected_link_href": resolved.key_link_href,
        "window_center": resolved.window_center,
        "window_width": resolved.window_width,
        "dicom_url": dicom_url,
        "metadata_summary": metadata,
        "roi_bbox": roi_bbox,
        "modes": mode_results,
    }
    (output_dir / f"{case['id']}.json").write_text(json.dumps(case_result, indent=2) + "\n")
    return case_result


def build_openai_final(
    output_dir: Path,
    case_results: list[dict[str, Any]],
    seeing_model: str,
    explaining_model: str,
    benchmark_modes: tuple[str, ...],
    detail: str,
) -> dict[str, Any]:
    mode_summaries: dict[str, Any] = {}
    for mode in benchmark_modes:
        rows = []
        for case_result in case_results:
            mode_result = case_result["modes"][mode]
            rows.append(
                {
                    "case_id": case_result["id"],
                    "confidence": mode_result["confidence"],
                    "verdict": mode_result["verdict"],
                    "diagnosis": mode_result["diagnosis"],
                }
            )
        mode_summaries[mode] = summarize_mode(rows)

    final = {
        "benchmark_name": "openai-responses-dicom-single-slice-benchmark",
        "run_date": "2026-04-15",
        "provider": "openai-responses",
        "seeing_model": seeing_model,
        "explaining_model": explaining_model,
        "benchmark_modes": list(benchmark_modes),
        "detail": detail,
        "case_mix": {"CT_or_CTA": 7, "MRI": 3},
        "notes": [
            "This benchmark uses the OpenAI Responses API with a split seeing -> explaining flow.",
            "The benchmark modes are image-only, image+metadata, and image+metadata+ROI.",
            "ROI crops are generated from the teaching-case instance annotations when available.",
            "This benchmark is for research only; OpenAI's vision guide explicitly says the models are not suitable for interpreting specialized medical images like CT scans for medical advice.",
        ],
        "scoring_rules": {
            "match": "Diagnosis text contains the target concept.",
            "partial": "Diagnosis captures a clinically related but incomplete target, such as appendicitis instead of perforated appendicitis.",
            "miss": "Diagnosis points to a different pathology.",
        },
        "mode_summaries": mode_summaries,
        "cases": case_results,
    }
    (output_dir / "results.json").write_text(json.dumps(final, indent=2) + "\n")
    return final


def load_completed_openai_case(output_dir: Path, case_id: str, benchmark_modes: tuple[str, ...]) -> dict[str, Any] | None:
    path = output_dir / f"{case_id}.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    modes = payload.get("modes")
    if not isinstance(modes, dict):
        return None
    if not all(mode in modes for mode in benchmark_modes):
        return None
    return payload


def build_codex_final(output_dir: Path, model: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {"total_cases": 0, "match": 0, "partial": 0, "miss": 0}
    for result in results:
        summary["total_cases"] += 1
        summary[result["verdict"]] += 1

    final = {
        "benchmark_name": "codex-dicom-single-slice-public-benchmark",
        "run_date": "2026-04-15",
        "model": model,
        "provider": "openai via codex exec",
        "summary": {
            **summary,
            "strict_top1_accuracy": summary["match"] / summary["total_cases"],
            "directionally_useful_accuracy": (summary["match"] + summary["partial"]) / summary["total_cases"],
        },
        "case_mix": {"CT_or_CTA": 7, "MRI": 3},
        "notes": [
            "Each case uses one published pathology-bearing key-image link from the public teaching page.",
            "The selected auto-scroll link index is fixed per case because some pages include generic or non-target links.",
            "The pulmonary embolism scoring regex is intentionally strict to avoid accidental substring matches.",
        ],
        "scoring_rules": {
            "match": "Diagnosis text contains the target concept.",
            "partial": "Diagnosis captures a clinically related but incomplete target, such as appendicitis instead of perforated appendicitis.",
            "miss": "Diagnosis points to a different pathology.",
        },
        "prompt_template": CODEX_PROMPT_TEMPLATE.strip(),
        "cases": results,
    }
    (output_dir / "results.json").write_text(json.dumps(final, indent=2) + "\n")
    return final


def parse_modes(value: str) -> tuple[str, ...]:
    raw = tuple(part.strip() for part in value.split(",") if part.strip())
    invalid = sorted(set(raw) - set(DEFAULT_OPENAI_MODES))
    if invalid:
        raise argparse.ArgumentTypeError(f"Unsupported benchmark mode(s): {', '.join(invalid)}")
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the public DICOM benchmark.")
    parser.add_argument("--provider", choices=["codex", "openai"], default="codex")
    parser.add_argument("--output-dir", required=True, help="Directory where benchmark files and results.json will be written.")
    parser.add_argument("--model", default="gpt-5.4", help="Codex model name for provider=codex.")
    parser.add_argument("--seeing-model", default="gpt-5.4", help="OpenAI seeing-pass model for provider=openai.")
    parser.add_argument("--explaining-model", default="gpt-5.4-mini", help="OpenAI explaining-pass model for provider=openai.")
    parser.add_argument(
        "--benchmark-modes",
        type=parse_modes,
        default=DEFAULT_OPENAI_MODES,
        help="Comma-separated OpenAI modes: image-only,image+metadata,image+metadata+roi",
    )
    parser.add_argument("--detail", default="original", help="Image detail level for OpenAI input_image parts.")
    parser.add_argument("--openai-api-base", default="https://api.openai.com/v1", help="Base URL for the OpenAI API.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.provider == "codex":
        results = [evaluate_case_codex(case, output_dir, args.model) for case in CASES]
        final = build_codex_final(output_dir, args.model, results)
        print(json.dumps(final["summary"], indent=2))
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required for provider=openai")

    case_results = []
    for case in CASES:
        cached = load_completed_openai_case(output_dir, case["id"], args.benchmark_modes)
        if cached is not None:
            case_results.append(cached)
            continue

        case_dir = output_dir / case["id"]
        if case_dir.exists():
            shutil.rmtree(case_dir)

        case_results.append(
            evaluate_case_openai(
                case=case,
                output_dir=output_dir,
                api_key=api_key,
                api_base=args.openai_api_base,
                seeing_model=args.seeing_model,
                explaining_model=args.explaining_model,
                benchmark_modes=args.benchmark_modes,
                detail=args.detail,
            )
        )
    
    final = build_openai_final(
        output_dir=output_dir,
        case_results=case_results,
        seeing_model=args.seeing_model,
        explaining_model=args.explaining_model,
        benchmark_modes=args.benchmark_modes,
        detail=args.detail,
    )
    print(json.dumps(final["mode_summaries"], indent=2))


if __name__ == "__main__":
    main()
