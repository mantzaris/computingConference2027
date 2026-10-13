"""Build and check the separate anonymous Computing Conference 2027 draft.

Run from GoT-war: python3 scripts/build_narrative_paper.py
Uses retained svproc and publication figures. No inference or old-file updates.
TeX products and page previews stay under .private/narrative_maps_2027/.
"""
from __future__ import annotations

import hashlib
import json
import lzma
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper/narrative_maps_2027"
BUILD = ROOT / ".private/narrative_maps_2027"


def run(args, cwd=PAPER, env=None):
    result = subprocess.run(args, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(" ".join(map(str, args)) + "\n" + result.stdout[-6000:])
    return result.stdout


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_retained_science():
    """Audit manuscript transcriptions, using existing solvers without new generation."""
    sys.path.insert(0, str(ROOT / "src"))
    from got_war.simple_stories import reference_world, verify_references, mutation_checks
    import v4_reproduce

    data = v4_reproduce.load()
    records, reproduced = v4_reproduce.verify(data)
    counts = {
        "cases": len(records),
        "variables": sum(len(r["representation"]["variables"]) for r in records),
        "relationships": sum(len(r["representation"]["edges"]) for r in records),
        "questions": sum(len(r["queries"]) for r in records),
        "scenario_disagreements": sum(len({tuple(a["result"]["values"]) for a in q["conditional"]}) > 1
                                      for r in records for q in r["queries"]),
        "broad_sets_both_binary_values": sum(q["partial_result"]["values"] == [0, 1]
                                             for r in records for q in r["queries"]),
        "episode_pages": len(data["source_acquisition"]["sources"]),
        "scene_containers": data["source_acquisition"]["acquired_scenes"],
    }
    assert counts == dict(cases=6, variables=69, relationships=71, questions=18,
                          scenario_disagreements=6, broad_sets_both_binary_values=18,
                          episode_pages=41, scene_containers=924), counts
    equations = {
        "blackwater": {"T": "W", "I": "S", "D": "T and I and B"},
        "red_wedding": {"P": "N and H", "X": "T and P"},
        "bolton": {"J": "B", "E": "J and S", "R": "A and V", "H": "E and not R",
                   "K": "P and W", "Y": "K and P"},
        "astapor": {"B": "O", "C": "B", "U": "C and Q", "F": "D", "R": "E and S",
                    "Y": "S and E and R"},
    }
    alternatives = {
        "blackwater": ("Y", ["F and (D or C)", "F or (D and C)"]),
        "red_wedding": ("T", ["G and A", "A"]),
        "bolton": ("P", ["G and R and not H", "G and not H"]),
        "astapor": ("S", ["U and F", "U"]),
    }
    for case, expected in equations.items():
        scenarios = data["generation_drafts"][case]["scenarios"]
        for scenario in scenarios:
            assert all(scenario["equations"][k] == v for k,v in expected.items()), case
        key, functions = alternatives[case]
        assert [s["equations"][key] for s in scenarios] == functions, case

    frozen = json.loads((ROOT / "experiments/simple_stories/frozen.json").read_text())
    expected_references = {"crow": {"A":"S", "R":"I and A", "T":"I and (B or R)", "D":"T"},
                           "humpty": {"D":"F", "R":"D and A and E", "Y":"D and not R"},
                           "wolf": {"L":"F", "N":"W", "V":"N and not L", "H":"W and not V"}}
    examples = {"crow": [({"A":0}, 0), ({"A":0,"B":1}, 1)],
                "humpty": [({"E":1}, 0), ({"E":1,"A":0}, 1)],
                "wolf": [({"F":0}, 0), ({"F":0,"N":0}, 1)]}
    for story in frozen["stories"]:
        ref = story["reference"]
        assert {v["id"]:v["equation"] for v in ref["variables"] if v["equation"]} == expected_references[story["id"]]
        for intervention, answer in examples[story["id"]]:
            assert reference_world(ref, intervention)[ref["outcome"]] == answer
    reference_checks = verify_references(frozen)
    mutations = mutation_checks()
    assert len(reference_checks) == 12 and all(m["detected"] for m in mutations)
    stories = json.loads(lzma.decompress((ROOT / "experiments/simple_stories/records.json.xz").read_bytes()))
    baseline = stories["result_snapshot"]["primary"]
    assert baseline["direct_correct"] == baseline["questions"] == 12
    assert baseline["controlled_compiled"] == baseline["natural_compiled"] == 0
    reassessment = json.loads((ROOT / "experiments/simple_stories/reassessment.json").read_text())
    facts = {r["id"]: [len(r["archived_factual_audit"]["supported"]),
                         len(r["archived_factual_audit"]["supported"])+len(r["archived_factual_audit"]["unsupported"])]
             for r in reassessment["records"]}
    assert list(facts.values()) == [[4,6],[6,6],[8,8],[5,6],[8,8],[8,8]]

    benchmark = json.loads((ROOT / "results/v2/test_summary.json").read_text())
    methods = {r["method"]:r["metrics"] for r in benchmark["tables"] if r["condition"] == "all"}
    identified = {k:round(100*methods[k]["identified_correct"]["estimate"], 1) for k in ("B0","B2","ALT","FULL")}
    assert identified == dict(B0=56.7, B2=77.8, ALT=77.8, FULL=77.8)
    assert round(100*methods["CARRY"]["identified_correct"]["estimate"],1) == 86.2
    changed = {k:round(100*methods[k]["changed_correct"]["estimate"],1) for k in ("B0","B2","CARRY")}
    assert changed == dict(B0=54.6, B2=80.0, CARRY=0)
    difference = next(d for d in benchmark["paired_differences"] if d["left"]=="B2" and d["right"]=="B0")["metrics"]["identified_correct"]
    delta = {k:round(100*difference[k],1) for k in ("estimate","lower","upper")}
    assert delta == dict(estimate=21.0, lower=9.6, upper=32.8)
    failed = round(72*(1-benchmark["components"]["synthesis_after_repair"]["estimate"]))
    assert benchmark["planned_scms"] == 72 and failed == 16 and benchmark["uncertainty"]["replicates"] == 5000
    usage = data["usage"]
    assert usage["generated_tokens"] == 36659 and usage["requests"] == 17
    assert round(usage["request_seconds"]/60,1) == 7.9 and round(usage["service_seconds"]/60,1) == 31.5
    assert stories["resource_usage"]["generated_tokens"] == 18814
    assert round(stories["resource_usage"]["service_seconds"]/60,2) == 6.26
    artifacts = ["results/v4/reproduction.json.xz", "results/v2/test_summary.json",
                 "experiments/simple_stories/frozen.json", "experiments/simple_stories/records.json.xz",
                 "experiments/simple_stories/reassessment.json"]
    return {"artifact_hashes": {p:sha(ROOT/p) for p in artifacts}, "application_counts": counts,
            "application_reproduction": reproduced, "manuscript_equations_match_archives": True,
            "worked_interventions_reproduced": examples, "reference_answers": len(reference_checks),
            "mutations_detected": len(mutations), "story_facts": facts,
            "benchmark_identified_percent": identified, "benchmark_changed_percent": changed,
            "benchmark_paired_difference_pp": delta, "failed_benchmark_syntheses": failed,
            "scope": "Arithmetic, expression transcription and execution checks; semantic judgments still require substantive review."}


def build():
    science = check_retained_science()
    BUILD.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TEXINPUTS"] = str(ROOT / "paper/template") + os.pathsep + env.get("TEXINPUTS", "")
    env["BIBINPUTS"] = str(PAPER) + os.pathsep + env.get("BIBINPUTS", "")
    tex = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
           "-file-line-error", "-output-directory=" + str(BUILD), "manuscript.tex"]
    run(tex, env=env)
    run(["bibtex", "manuscript"], cwd=BUILD, env=env)
    for _ in range(3):
        run(tex, env=env)
    run(["gs", "-q", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite",
         "-dCompatibilityLevel=1.5", "-dEmbedAllFonts=true", "-dSubsetFonts=true",
         "-dCompressFonts=true", "-dOmitInfoDate=true", "-dOmitID=true",
         "-sOutputFile=" + str(PAPER / "manuscript.pdf"), str(BUILD / "manuscript.pdf")])

    text = run(["pdftotext", "-layout", str(PAPER / "manuscript.pdf"), "-"])
    (BUILD / "manuscript.txt").write_text(text)
    info = run(["pdfinfo", str(PAPER / "manuscript.pdf")])
    fonts = run(["pdffonts", str(PAPER / "manuscript.pdf")])
    log = (BUILD / "manuscript.log").read_text()
    aux = (BUILD / "manuscript.aux").read_text()
    source = (PAPER / "manuscript.tex").read_text()
    abstract = source.split(r"\begin{abstract}")[1].split(r"\keywords")[0]
    abstract_words = len(re.findall(r"\b[\w]+(?:[-'][\w]+)*\b", abstract))
    captions = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^\n]+)\}",
                               (PAPER / "captions.tex").read_text()))
    caption_words = {k: len(re.findall(r"\b[\w]+(?:[-'][\w]+)*\b", v)) for k,v in captions.items()}
    pages = int(re.search(r"Pages:\s+(\d+)", info)[1])
    main_pages = int(re.search(r"\\newlabel\{sec:main-end\}\{\{[^}]*\}\{(\d+)\}", aux)[1])
    citation_keys = set(re.findall(r"\\bibcite\{([^}]+)\}", aux))
    cited_keys = set(k for match in re.findall(r"\\citation\{([^}]+)\}", aux) for k in match.split(","))
    checks = {
        "abstract_150_to_250_words": 150 <= abstract_words <= 250,
        "main_at_most_18_pages": main_pages <= 18,
        "references_and_appendices_at_most_7_pages": pages-main_pages <= 7,
        "all_references_cited": citation_keys == cited_keys,
        "no_unresolved_references": not re.search(r"(?:undefined|Rerun to get cross-references right)", log),
        "no_overfull_boxes": "Overfull" not in log,
        "captions_15_to_30_words": all(15 <= n <= 30 for n in caption_words.values()),
        "all_pdf_fonts_embedded": not re.search(r"\sno\s+(?:yes|no)\s+(?:yes|no)\s+\d+\s+\d+\s*$", fonts, re.M),
        "author_field_empty": not re.search(r"^Author:[ \t]*[^ \t\r\n]", info, re.M),
        "no_identifying_project_strings": not any(s in (text+info).lower() for s in
            ["mantzaris", "computingconference2027", "github.com", "/home/resort", "author information"]),
        "actual_template_width": "PAPER-TEXTWIDTH: 347.12354pt" in log,
    }
    figure_manifest = json.loads((ROOT / "figures/publication/manifest.json").read_text())
    figure_hashes = {}
    for item in figure_manifest["items"]:
        path = ROOT / (item["stem"] + ".pdf")
        figure_hashes[str(path.relative_to(ROOT))] = sha(path)
        assert sha(path) == item["files"][".pdf"]["sha256"], path
    result = {
        "artifact": "paper/narrative_maps_2027/manuscript.pdf",
        "abstract_words": abstract_words, "pages": pages, "main_pages": main_pages,
        "references_appendix_pages": pages-main_pages, "text_width_mm": 122,
        "caption_words": caption_words, "references": len(citation_keys),
        "figures": len(figure_hashes), "figure_hashes": figure_hashes,
        "template_sha256": sha(ROOT / "paper/template/svproc.cls"),
        "source_sha256": sha(PAPER / "manuscript.tex"),
        "bibliography_sha256": sha(PAPER / "references.bib"),
        "pdf_sha256": sha(PAPER / "manuscript.pdf"), "pdf_bytes": (PAPER / "manuscript.pdf").stat().st_size,
        "checks": checks,
        "retained_science": science,
        "inspection_note": "Automated checks complement the page-by-page editorial inspection documented in EDITORIAL.md.",
    }
    (PAPER / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k not in {"figure_hashes", "caption_words", "retained_science"}}, indent=2))
    if not all(checks.values()):
        raise SystemExit("Verification failed: " + ", ".join(k for k,v in checks.items() if not v))


if __name__ == "__main__":
    build()
