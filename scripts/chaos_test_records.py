#!/usr/bin/env python3
import csv
import io
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path
from dataclasses import dataclass


DOMAIN = "shamboozie.com."
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = str(REPO_ROOT / "src")
SUPPORTED_TYPES = ("A", "AAAA", "CNAME", "MX", "NS", "SRV", "TXT")
COMMAND_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class RecordCase:
    record_type: str
    name: str
    add_data: str
    update_data: str
    ttl: int
    update_ttl: int
    priority: int | None = None
    update_priority: int | None = None
    weight: int | None = None
    update_weight: int | None = None
    port: int | None = None
    update_port: int | None = None


def build_cases() -> list[RecordCase]:
    suffix = f"{int(time.time())}-{random.randint(1000, 9999)}"
    base = f"chaos-{suffix}"
    shuffled_types = list(SUPPORTED_TYPES)
    random.shuffle(shuffled_types)

    definitions = {
        "A": ("198.51.100.10", "198.51.100.11"),
        "AAAA": ("2001:db8::10", "2001:db8::11"),
        "CNAME": ("target1.example.net.", "target2.example.net."),
        "MX": ("mail1.example.net.", "mail2.example.net."),
        "NS": ("ns1.example.net.", "ns2.example.net."),
        "SRV": ("sip1.example.net.", "sip2.example.net."),
        "TXT": (f"chaos-text-{suffix}-1", f"chaos-text-{suffix}-2"),
    }

    cases: list[RecordCase] = []
    for index, record_type in enumerate(shuffled_types, start=1):
        add_data, update_data = definitions[record_type]
        cases.append(
            RecordCase(
                record_type=record_type,
                name=f"{base}-{index}".lower() if record_type != "SRV" else f"_sip._tcp.{base}-{index}".lower(),
                add_data=add_data,
                update_data=update_data,
                ttl=300 + index,
                update_ttl=600 + index,
                priority=10 if record_type == "MX" else 20 if record_type == "SRV" else None,
                update_priority=30 if record_type == "MX" else 40 if record_type == "SRV" else None,
                weight=5 if record_type == "SRV" else None,
                update_weight=10 if record_type == "SRV" else None,
                port=5060 if record_type == "SRV" else None,
                update_port=5061 if record_type == "SRV" else None,
            )
        )
    return cases


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = SRC_DIR if not env.get("PYTHONPATH") else f"{SRC_DIR}:{env['PYTHONPATH']}"
    try:
        return subprocess.run(
            [sys.executable, "-m", "conoha_dns_cli.main", *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
            cwd=REPO_ROOT,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        raise RuntimeError(
            f"command timed out after {COMMAND_TIMEOUT_SECONDS}s: {[sys.executable, '-m', 'conoha_dns_cli.main', *args]!r}\n"
            f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        ) from exc


def list_records() -> list[dict[str, str]]:
    result = run_cli("-l", DOMAIN, "--output", "csv")
    if result.returncode != 0:
        raise RuntimeError(
            f"list failed with exit={result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    reader = csv.DictReader(io.StringIO(result.stdout))
    return list(reader)


def find_record_id(name: str, record_type: str, data: str) -> str | None:
    for row in list_records():
        if row["Name"] == f"{name}.{DOMAIN}" and row["Type"] == record_type and row["Data"] == data:
            return row["ID"]
    return None


def extract_id(output: str) -> str | None:
    match = re.search(r"ID:\s*([0-9a-f]{8})", output)
    return match.group(1) if match else None


def main() -> int:
    cases = build_cases()
    failures: list[str] = []

    for case in cases:
        label = f"{case.record_type}:{case.name}"
        record_id: str | None = None

        try:
            add_args = ["-ar", DOMAIN, case.name, case.record_type, case.add_data, "--ttl", str(case.ttl)]
            if case.priority is not None:
                add_args.extend(["--priority", str(case.priority)])
            if case.weight is not None:
                add_args.extend(["--weight", str(case.weight)])
            if case.port is not None:
                add_args.extend(["--port", str(case.port)])
            add = run_cli(*add_args)
        except RuntimeError as exc:
            failures.append(f"{label} add failed\n{exc}")
            continue
        if add.returncode != 0:
            failures.append(
                f"{label} add failed (exit={add.returncode})\nstdout:\n{add.stdout}\nstderr:\n{add.stderr}"
            )
            continue

        try:
            record_id = extract_id(add.stdout) or find_record_id(case.name, case.record_type, case.add_data)
        except RuntimeError as exc:
            failures.append(f"{label} add verification failed\n{exc}")
            continue
        if not record_id:
            failures.append(f"{label} add succeeded but record ID could not be resolved")
            continue

        try:
            listed_id = find_record_id(case.name, case.record_type, case.add_data)
        except RuntimeError as exc:
            failures.append(f"{label} list verification failed\n{exc}")
            listed_id = None
        if listed_id != record_id:
            failures.append(
                f"{label} list verification failed expected id={record_id!r} got id={listed_id!r}"
            )

        try:
            update_args = [
                "-ur",
                DOMAIN,
                record_id,
                "--new-data",
                case.update_data,
                "--new-ttl",
                str(case.update_ttl),
            ]
            if case.update_priority is not None:
                update_args.extend(["--new-priority", str(case.update_priority)])
            if case.update_weight is not None:
                update_args.extend(["--new-weight", str(case.update_weight)])
            if case.update_port is not None:
                update_args.extend(["--new-port", str(case.update_port)])
            update = run_cli(*update_args)
        except RuntimeError as exc:
            failures.append(f"{label} update failed\n{exc}")
            update = None
        if update is not None and update.returncode != 0:
            failures.append(
                f"{label} update failed (exit={update.returncode})\nstdout:\n{update.stdout}\nstderr:\n{update.stderr}"
            )
        elif update is not None:
            try:
                updated_id = find_record_id(case.name, case.record_type, case.update_data)
            except RuntimeError as exc:
                failures.append(f"{label} update verification failed\n{exc}")
                updated_id = None
            if updated_id != record_id:
                failures.append(
                    f"{label} update verification failed expected id={record_id!r} got id={updated_id!r}"
                )

        try:
            delete = run_cli("-dr", DOMAIN, record_id)
        except RuntimeError as exc:
            failures.append(f"{label} delete failed\n{exc}")
            continue
        if delete.returncode != 0:
            failures.append(
                f"{label} delete failed (exit={delete.returncode})\nstdout:\n{delete.stdout}\nstderr:\n{delete.stderr}"
            )
            continue

        try:
            deleted_add_id = find_record_id(case.name, case.record_type, case.add_data)
            deleted_update_id = find_record_id(case.name, case.record_type, case.update_data)
        except RuntimeError as exc:
            failures.append(f"{label} delete verification failed\n{exc}")
            continue
        if deleted_add_id is not None or deleted_update_id is not None:
            failures.append(
                f"{label} delete verification failed lingering ids add={deleted_add_id!r} update={deleted_update_id!r}"
            )

    if failures:
        print("FAILED TESTS")
        print("=" * 80)
        for index, failure in enumerate(failures, start=1):
            print(f"[{index}] {failure}")
            print("-" * 80)
        return 1

    print("All record lifecycle tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
