from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    module_dir = repo_root / "java" / "graph-runner"

    parser = argparse.ArgumentParser(
        description="Run GraphStream viewer for a .dgs file via the Java graph-runner module."
    )
    default_dgs = repo_root / "data" / "exports" / "all_2021_2021.dgs"
    parser.add_argument(
        "dgs_path",
        nargs="?",
        default=default_dgs,
        help="Path to .dgs file (default: data/exports/all_2021_2021.dgs)",
    )
    args = parser.parse_args()

    dgs_path = Path(args.dgs_path).expanduser()
    if not dgs_path.is_absolute():
        dgs_path = (repo_root / dgs_path).resolve()

    if not dgs_path.exists():
        print(f"DGS file not found: {dgs_path}", file=sys.stderr)
        candidates = list(repo_root.glob("**/*.dgs"))
        if candidates:
            print("Available .dgs files:", file=sys.stderr)
            for path in candidates:
                print(f"  - {path.relative_to(repo_root)}", file=sys.stderr)
        else:
            print("No .dgs files found in the repo.", file=sys.stderr)
            print(
                "Provide a .dgs path explicitly, e.g.:",
                "python scripts/run_graph_runner.py path\\to\\file.dgs",
                file=sys.stderr,
            )
        return 2

    mvn = shutil.which("mvn") or shutil.which("mvn.cmd") or shutil.which("mvn.bat")
    if not mvn:
        print(
            "Maven executable not found in PATH. Install Maven or add it to PATH.",
            file=sys.stderr,
        )
        return 3

    # Check if Maven build has been done
    target_classes = module_dir / "target" / "classes" / "org" / "example" / "graphrunner"
    if not target_classes.exists():
        print("Maven build not found. Running 'mvn package -q'...", file=sys.stderr)
        build_cmd = [mvn, "package", "-q"]
        result = subprocess.run(build_cmd, cwd=str(module_dir))
        if result.returncode != 0:
            print(f"Maven build failed with return code {result.returncode}", file=sys.stderr)
            return result.returncode

    env = dict(**{k: v for k, v in dict(**__import__("os").environ).items()})
    default_java_home = Path(r"C:\Program Files\Eclipse Adoptium\jdk-17.0.17.10-hotspot")
    java_home = env.get("JAVA_HOME")
    if default_java_home.exists():
        java_home = str(default_java_home)
        env["JAVA_HOME"] = java_home
        env["Path"] = f"{java_home}\\bin;{env.get('Path', '')}"

    java_exe = None
    if java_home:
        candidate = Path(java_home) / "bin" / "java.exe"
        if candidate.exists():
            java_exe = str(candidate)

    cmd = [
        mvn,
        "-q",
        "exec:java",
        "-Dexec.mainClass=org.example.graphrunner.Runner",
    ]
    if java_exe:
        cmd.append(f"-Dexec.javaExecutable={java_exe}")
    cmd.append(f"-Dexec.args={dgs_path}")

    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(module_dir), env=env)


if __name__ == "__main__":
    raise SystemExit(main())
