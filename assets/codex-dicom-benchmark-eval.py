#!/usr/bin/env python3
"""
Run the 10-case public Codex DICOM benchmark used in the blog post.

Requirements:
  - Codex CLI installed and authenticated
  - Python packages: numpy, pillow, pydicom

Example:
  python3 codex-dicom-benchmark-eval.py \
    --output-dir /tmp/codex-dicom-benchmark \
    --model gpt-5.4
"""

from __future__ import annotations

import argparse
import gzip
import html
import json
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import pydicom
from PIL import Image


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

PROMPT_TEMPLATE = """You are evaluating a single de-identified DICOM teaching-case slice for research only, not clinical care.
Return only the structured schema.
Use the attached image as primary evidence and the metadata only as supporting context.
Be specific about the single most likely diagnosis visible on this slice.

Metadata:
{metadata}
"""

SCHEMA = {
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
    match = re.search(r"var studydata = (\{.*?\});", page_html, re.S)
    if not match:
        raise ValueError("Could not find studydata JSON in page")
    return json.loads(match.group(1))


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


def render_dicom_png(dicom_bytes: bytes, png_path: Path, wc: float | None, ww: float | None) -> pydicom.Dataset:
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


def metadata_summary(case: dict[str, Any], studydata: dict[str, Any], series: dict[str, Any], ds: pydicom.Dataset) -> str:
    rows = [
        f"Case title: {studydata.get('name', case['title'])}",
        f"Published modality bucket: {case['modality']}",
        f"Series label: {series.get('label', '')}",
        f"Series modality: {series.get('modality', '')}",
        f"Study description: {ds.get('StudyDescription', '')}",
        f"Series description: {ds.get('SeriesDescription', '')}",
        f"Body part examined: {ds.get('BodyPartExamined', '')}",
        f"Image dimensions: {ds.get('Rows', '')} x {ds.get('Columns', '')}",
    ]
    return "\n".join(row for row in rows if not row.endswith(": "))


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

    proc = subprocess.run(
        cmd,
        input=prompt,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "codex exec failed\n"
            f"stdout:\n{proc.stdout}\n\n"
            f"stderr:\n{proc.stderr}"
        )
    return json.loads(output_path.read_text())


def score_prediction(case: dict[str, Any], diagnosis: str) -> str:
    diagnosis_l = diagnosis.lower()
    if re.search(case["match_regex"], diagnosis_l):
        return "match"
    partial_regex = case.get("partial_regex")
    if partial_regex and re.search(partial_regex, diagnosis_l):
        return "partial"
    return "miss"


def evaluate_case(case: dict[str, Any], output_dir: Path, model: str) -> dict[str, Any]:
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
    schema_path.write_text(json.dumps(SCHEMA, indent=2) + "\n")

    metadata = metadata_summary(case, resolved.studydata, resolved.series, ds)
    prompt = PROMPT_TEMPLATE.format(metadata=metadata)
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the 10-case Codex DICOM benchmark.")
    parser.add_argument("--output-dir", required=True, help="Directory where case files and results.json will be written.")
    parser.add_argument("--model", default="gpt-5.4", help="Codex model name to use.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    results = [evaluate_case(case, output_dir, args.model) for case in CASES]

    summary = {"total_cases": 0, "match": 0, "partial": 0, "miss": 0}
    for result in results:
        summary["total_cases"] += 1
        summary[result["verdict"]] += 1

    final = {
        "benchmark_name": "codex-dicom-single-slice-public-benchmark",
        "run_date": "2026-04-15",
        "model": args.model,
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
        "prompt_template": PROMPT_TEMPLATE.strip(),
        "cases": results,
    }
    (output_dir / "results.json").write_text(json.dumps(final, indent=2) + "\n")
    print(json.dumps(final["summary"], indent=2))


if __name__ == "__main__":
    main()
