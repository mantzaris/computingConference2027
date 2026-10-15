"""Build and check the anonymous Computing Conference 2027 manuscript.

Run from GoT-war: python3 scripts/build_narrative_paper.py
Uses retained svproc and publication figures. No inference or old-file updates.
TeX products and page previews stay under .private/narrative_maps_2027/.
"""
from __future__ import annotations

import hashlib
import csv
import json
import lzma
import os
from pathlib import Path
import re
import shutil
import subprocess
import statistics
import sys
import tempfile

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


def check_bibliography(cited_keys):
    """Check entry identity and actual citation coverage, not bibliographic truth."""
    source = (PAPER / "references.bib").read_text()
    entries = re.split(r"(?m)^@", source)[1:]
    keys, titles, dois = [], [], []

    def field(entry, name):
        match = re.search(r"\b" + name + r"\s*=\s*\{", entry, re.I)
        if not match:
            return ""
        start, depth, end = match.end(), 1, match.end()
        while depth and end < len(entry):
            depth += (entry[end] == "{") - (entry[end] == "}")
            end += 1
        assert depth == 0, ("Unbalanced bibliography field", name)
        return entry[start:end-1]

    for entry in entries:
        keys.append(re.match(r"\w+\s*\{\s*([^,\s]+)\s*,", entry)[1])
        title = re.sub(r"[^a-z0-9]", "", field(entry, "title").lower())
        assert title, ("Missing bibliography title", keys[-1])
        titles.append(title)
        doi = field(entry, "doi").strip().lower()
        if doi:
            dois.append(doi)
    assert len(keys) == len(set(keys)), "Duplicate citation key"
    assert len(titles) == len(set(titles)), "Duplicate work title"
    assert len(dois) == len(set(dois)), "Duplicate work DOI"
    assert set(keys) == cited_keys, ("Bibliography/citation mismatch", set(keys) ^ cited_keys)
    assert len(keys) >= 25, "The manuscript requires at least 25 distinct references"
    return {"entries": len(keys), "all_entries_cited": True,
            "unique_keys_titles_and_dois": True, "minimum_25_met": True,
            "primary_source_audit": "paper/narrative_maps_2027/EDITORIAL.md",
            "scope": "Identity and coverage checks; publication details and claim support were checked against primary records and full texts in the editorial audit."}


def check_portable_build(input_files):
    """Compile only the manuscript folder's inputs, without project search paths."""
    env = os.environ.copy()
    for key in ("TEXINPUTS", "BIBINPUTS", "BSTINPUTS"):
        env.pop(key, None)
    with tempfile.TemporaryDirectory(prefix="standalone-", dir=BUILD) as temporary:
        bundle = Path(temporary)
        for name in input_files:
            shutil.copy2(PAPER / name, bundle / name)
        tex = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
               "-file-line-error", "-recorder", "manuscript.tex"]
        run(tex, cwd=bundle, env=env)
        run(["bibtex", "manuscript"], cwd=bundle, env=env)
        for _ in range(3):
            run(tex, cwd=bundle, env=env)
        expected = run(["pdftotext", "-layout", str(BUILD / "manuscript.pdf"), "-"])
        actual = run(["pdftotext", "-layout", str(bundle / "manuscript.pdf"), "-"])
        assert actual == expected, "Standalone compilation changed the rendered text"
        for line in (bundle / "manuscript.fls").read_text().splitlines():
            if line.startswith("INPUT "):
                path = (bundle / line[6:]).resolve()
                if ROOT in path.parents:
                    assert bundle in path.parents, ("External project input", path)
    return {"isolated_compilation": True, "rendered_text_matches": True,
            "project_inputs_self_contained": True,
            "input_hashes": {name: sha(PAPER / name) for name in input_files},
            "system_dependencies": "A LaTeX distribution with pdfLaTeX, BibTeX and the standard packages named in manuscript.tex, including newtx."}


def check_retained_science():
    """Audit manuscript transcriptions, using existing solvers without new generation."""
    sys.path.insert(0, str(ROOT / "src"))
    from got_war.simple_stories import reference_world, verify_references, mutation_checks
    import v4_reproduce

    data = v4_reproduce.load()
    records, reproduced = v4_reproduce.verify(
        data, source_check=(ROOT / ".private/v4/corpus.json").exists())
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

    # Re-execute the existing ignition question, including its local consequence.
    from got_war.v3.core import query
    blackwater = next(r for r in records if r["case"] == "blackwater")
    construction_results = []
    for scenario in blackwater["scenarios"]:
        damage = query(blackwater["representation"], scenario["family"], {"I": 0}, "D")
        victory = query(blackwater["representation"], scenario["family"], {"I": 0}, "Y")
        assert damage["values"] == [0] and victory["values"] == [1]
        construction_results.append({"scenario": scenario["id"], "do": {"I": 0},
                                     "fleet_damage": damage["values"], "assault_repelled": victory["values"]})
    proposal_audit = []
    for filename, excerpt in [
        ("pass_00.json", "Tyrion decides to take control of wildfire"),
        ("pass_01.json", "Tyrion launches a flaming arrow that ignites the wildfire on the water"),
    ]:
        relative = "runs/application_v4_20261013/qwen/blackwater/" + filename
        metadata = next(r for r in data["qwen"] if r["file"] == relative)
        path = ROOT / relative
        if path.exists():
            raw = json.loads(path.read_text())["raw"]["choices"][0]["message"]["content"]
            assert hashlib.sha256(raw.encode()).hexdigest() == metadata["content_sha256"]
            assert excerpt in raw
        proposal_audit.append({"record": relative, "content_sha256": metadata["content_sha256"],
                               "raw_proposal_inspected": path.exists()})

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
    protocol = json.loads((ROOT / "configs/v2_frozen_protocol.json").read_text())["design"]
    assert protocol["independent_scms"] == 120
    assert protocol["splits"] == {"development": 24, "calibration": 24, "test": 72}
    strata = [s for s in protocol["strata"] if s["split"] == "test"]
    question_counts = {k: sum(s.get(k, 0) for s in strata) for k in
                       ("identified_changed", "identified_unchanged", "underidentified")}
    assert sum(question_counts.values()) == 1080
    with (ROOT / "results/v2/test_scm_scores.csv").open() as stream:
        scores = list(csv.DictReader(stream))
    for method in ("B0", "B2", "CARRY"):
        for metric in ("identified_correct", "changed_correct"):
            values = [float(r[metric]) for r in scores if r["method"] == method and r[metric]]
            assert len(values) == methods[method][metric]["scms"]
            assert abs(statistics.mean(values) - methods[method][metric]["estimate"]) < 1e-12
    identified = {k:round(100*methods[k]["identified_correct"]["estimate"], 1) for k in ("B0","B2","ALT","FULL")}
    assert identified == dict(B0=56.7, B2=77.8, ALT=77.8, FULL=77.8)
    assert round(100*methods["CARRY"]["identified_correct"]["estimate"],1) == 86.2
    changed = {k:round(100*methods[k]["changed_correct"]["estimate"],1) for k in ("B0","B2","CARRY")}
    assert changed == dict(B0=54.6, B2=80.0, CARRY=0)
    difference = next(d for d in benchmark["paired_differences"] if d["left"]=="B2" and d["right"]=="B0")["metrics"]["identified_correct"]
    delta = {k:round(100*difference[k],1) for k in ("estimate","lower","upper")}
    assert delta == dict(estimate=21.0, lower=9.6, upper=32.8)
    paired = {method: {r["id"]: float(r["identified_correct"]) for r in scores if r["method"] == method}
              for method in ("B0", "B2")}
    assert paired["B0"].keys() == paired["B2"].keys()
    recomputed_delta = statistics.mean(paired["B2"][k] - paired["B0"][k] for k in paired["B0"])
    assert abs(recomputed_delta - difference["estimate"]) < 1e-12
    assert all(methods[k]["identified_correct"]["scms"] == 72 and
               methods[k]["changed_correct"]["scms"] == 40 for k in ("B0", "B2", "CARRY"))
    failed = round(72*(1-benchmark["components"]["synthesis_after_repair"]["estimate"]))
    assert benchmark["planned_scms"] == 72 and failed == 16 and benchmark["uncertainty"]["replicates"] == 5000
    usage = data["usage"]
    assert usage["generated_tokens"] == 36659 and usage["requests"] == 17
    assert round(usage["request_seconds"]/60,1) == 7.9 and round(usage["service_seconds"]/60,1) == 31.5
    assert stories["resource_usage"]["generated_tokens"] == 18814
    assert round(stories["resource_usage"]["service_seconds"]/60,2) == 6.26
    artifacts = ["results/v4/reproduction.json.xz", "results/v2/test_summary.json",
                 "results/v2/test_scm_scores.csv", "configs/v2_frozen_protocol.json",
                 "experiments/simple_stories/frozen.json", "experiments/simple_stories/records.json.xz",
                 "experiments/simple_stories/reassessment.json"]
    return {"artifact_hashes": {p:sha(ROOT/p) for p in artifacts}, "application_counts": counts,
            "application_reproduction": reproduced, "manuscript_equations_match_archives": True,
            "blackwater_construction_trace": {"proposal_records": proposal_audit,
                                              "intervention_results": construction_results,
                                              "revision_history": blackwater["generation"]["revision_history"]},
            "worked_interventions_reproduced": examples, "reference_answers": len(reference_checks),
            "mutations_detected": len(mutations), "story_facts": facts,
            "benchmark_identified_percent": identified, "benchmark_changed_percent": changed,
            "benchmark_paired_difference_pp": delta,
            "benchmark_unrounded_difference": recomputed_delta,
            "benchmark_evaluation_units": {"identified_scms": 72, "changing_scms": 40},
            "benchmark_question_counts": question_counts,
            "failed_benchmark_syntheses": failed,
            "scope": "Arithmetic, expression transcription, passage identity and execution checks; these do not establish independent semantic adjudication."}


def write_benchmark_values():
    """Typeset the archived estimates directly, rounding only at presentation."""
    archive = ROOT / "results/v2/test_summary.json"
    benchmark = json.loads(archive.read_text())
    methods = {r["method"]: r["metrics"] for r in benchmark["tables"] if r["condition"] == "all"}
    difference = next(d for d in benchmark["paired_differences"]
                      if d["left"] == "B2" and d["right"] == "B0")["metrics"]["identified_correct"]
    lines = ["% Generated by scripts/build_narrative_paper.py from results/v2/test_summary.json.",
             "% Archive SHA256: " + sha(archive)]
    for name, key in [("ExecutionGain", "estimate"), ("ExecutionLower", "lower"), ("ExecutionUpper", "upper")]:
        lines.append("\\newcommand{\\" + name + "}{" + f"{100*difference[key]:.1f}" + "}")
    lines += [r"\newcommand{\BenchmarkTable}{%", r"\begin{tabular}{@{}lrr@{}}", r"\toprule",
              r"Method & Identified (\%) & Changing (\%) \\",
              r" & 72 SCMs & 40 SCMs \\", r"\midrule"]
    for method, label in [("B0", "Direct answers"), ("B2", "Synthesis and execution"), ("CARRY", "Factual carry-forward")]:
        values = [f"{100*methods[method][metric]['estimate']:.1f}" for metric in ("identified_correct", "changed_correct")]
        lines.append(label + " & " + " & ".join(values) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", "}"]
    (PAPER / "benchmark_values.tex").write_text("\n".join(lines) + "\n")


def build():
    science = check_retained_science()
    write_benchmark_values()
    BUILD.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop("TEXINPUTS", None)
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
    rendered_captions = re.findall(r"^Fig\. \d+\..+?(?=\n\s*\n|\f|\Z)", text, re.M | re.S)
    caption_lines = [len(c.strip().splitlines()) for c in rendered_captions]
    pages = int(re.search(r"Pages:\s+(\d+)", info)[1])
    main_pages = int(re.search(r"\\newlabel\{sec:main-end\}\{\{[^}]*\}\{(\d+)\}", aux)[1])
    citation_keys = set(re.findall(r"\\bibcite\{([^}]+)\}", aux))
    cited_keys = set(k for match in re.findall(r"\\citation\{([^}]+)\}", aux) for k in match.split(","))
    bibliography = check_bibliography(cited_keys)
    checks = {
        "abstract_150_to_250_words": 150 <= abstract_words <= 250,
        "main_at_most_18_pages": main_pages <= 18,
        "references_and_appendices_at_most_7_pages": pages-main_pages <= 7,
        "all_references_cited": citation_keys == cited_keys,
        "no_unresolved_references": not re.search(r"(?:undefined|Rerun to get cross-references right)", log),
        "no_overfull_boxes": "Overfull" not in log,
        "captions_15_to_30_words": all(15 <= n <= 30 for n in caption_words.values()),
        "seven_figure_captions_at_most_two_lines": len(caption_lines) == 7 and max(caption_lines) <= 2,
        "all_pdf_fonts_embedded": not re.search(r"\sno\s+(?:yes|no)\s+(?:yes|no)\s+\d+\s+\d+\s*$", fonts, re.M),
        "author_field_empty": not re.search(r"^Author:[ \t]*[^ \t\r\n]", info, re.M),
        "no_identifying_project_strings": not any(s in (text+info).lower() for s in
            ["mantzaris", "computingconference2027", "github.com", "/home/resort", "author information"]),
        "actual_template_width": "PAPER-TEXTWIDTH: 347.12354pt" in log,
        "no_editorial_status_language": not re.search(
            r"this draft|temporary|pending|awaits? (?:author|review)|before submission|authors must|TODO|placeholder",
            text, re.I),
        "plain_manuscript_punctuation": not any(s in source for s in ["\u2014", "\u2013", "\u00a0", "\u202f", "~", "---"]),
        "one_ai_declaration": text.count("Declaration on Generative AI") == 1,
    }
    figure_manifest = json.loads((ROOT / "figures/publication/manifest.json").read_text())
    figure_hashes = {}
    for item in figure_manifest["items"]:
        path = ROOT / (item["stem"] + ".pdf")
        figure_hashes[str(path.relative_to(ROOT))] = sha(path)
        assert sha(path) == item["files"][".pdf"]["sha256"], path
        assert sha(PAPER / path.name) == sha(path), ("Figure copy differs", path.name)
    template_files = ["svproc.cls", "aliascnt.sty", "remreset.sty"]
    for name in template_files:
        assert sha(PAPER / name) == sha(ROOT / "paper/template" / name), name
    input_files = (["manuscript.tex", "captions.tex", "benchmark_values.tex", "references.bib"]
                   + template_files + [Path(path).name for path in figure_hashes])
    portability = check_portable_build(input_files)
    result = {
        "artifact": "paper/narrative_maps_2027/manuscript.pdf",
        "abstract_words": abstract_words, "pages": pages, "main_pages": main_pages,
        "references_appendix_pages": pages-main_pages, "text_width_mm": 122,
        "caption_words": caption_words, "references": len(citation_keys),
        "bibliography_audit": bibliography,
        "rendered_caption_lines": caption_lines,
        "conference_requirements_checked": {"date": "2026-10-14",
            "url": "https://saiconference.com/Computing/CallforPapers",
            "anonymous_review": True, "main_page_limit": 18, "additional_page_limit": 7,
            "abstract_word_limits": [150, 250], "generative_ai_declaration_required": True},
        "figures": len(figure_hashes), "figure_hashes": figure_hashes,
        "template_sha256": sha(PAPER / "svproc.cls"),
        "portability": portability,
        "source_sha256": sha(PAPER / "manuscript.tex"),
        "bibliography_sha256": sha(PAPER / "references.bib"),
        "benchmark_values_sha256": sha(PAPER / "benchmark_values.tex"),
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
