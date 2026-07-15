from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"
RESULTS_DIR = Path(__file__).parent / "results"


def _load_golden_set() -> list[dict]:
    data = json.loads(GOLDEN_SET_PATH.read_text())
    return data["questions"]


def run(questions: list[dict], live: bool) -> dict:
    from core.sql_generator import generate_sql, generate_and_run
    from core.bq_executor import estimate_cost
    from eval.grading import grade_sql

    results = []
    t_start = time.perf_counter()

    for i, spec in enumerate(questions, 1):
        qid = spec["id"]
        question = spec["question"]
        print(f"[{i}/{len(questions)}] {qid} — {question}")

        entry = {"id": qid, "question": question}
        try:
            if live:
                sql, df = generate_and_run(question)
                entry["rows_returned"] = int(len(df)) if df is not None else 0
            else:
                sql = generate_sql(question)
                cost = estimate_cost(sql)  
                entry["dry_run_bytes"] = cost.bytes_processed

            entry["sql"] = sql
            grade = grade_sql(sql, spec)
            entry["passed"] = grade.passed
            entry["checks"] = grade.checks
            entry["notes"] = grade.notes

        except Exception as e:
            entry["sql"] = entry.get("sql", "")
            entry["passed"] = False
            entry["checks"] = {}
            entry["notes"] = [f"Generation/execution failed: {e}"]

        status = "PASS" if entry["passed"] else "FAIL"
        print(f"    -> {status}" + (f" ({'; '.join(entry['notes'])})" if entry["notes"] else ""))
        results.append(entry)

    elapsed = time.perf_counter() - t_start
    passed_count = sum(1 for r in results if r["passed"])
    summary = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": "live" if live else "dry_run",
        "total": len(results),
        "passed": passed_count,
        "accuracy": round(passed_count / len(results), 4) if results else 0.0,
        "elapsed_seconds": round(elapsed, 1),
        "results": results,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--live", action="store_true", help="Actually execute queries against BigQuery (small real cost).")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N questions.")
    parser.add_argument("--id", type=str, default=None, help="Run only the question with this id.")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()

    questions = _load_golden_set()
    if args.id:
        questions = [q for q in questions if q["id"] == args.id]
        if not questions:
            print(f"No question with id={args.id!r} found.", file=sys.stderr)
            sys.exit(1)
    elif args.limit:
        questions = questions[: args.limit]

    summary = run(questions, live=args.live)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(summary, indent=2, default=str))

    print()
    print(f"{'=' * 50}")
    print(f"Accuracy: {summary['passed']}/{summary['total']} ({summary['accuracy']:.0%})")
    print(f"Mode: {summary['mode']} · {summary['elapsed_seconds']}s")
    print(f"Results saved -> {out_path}")
    print(f"{'=' * 50}")

    if summary["accuracy"] < 1.0:
        failed = [r["id"] for r in summary["results"] if not r["passed"]]
        print(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()