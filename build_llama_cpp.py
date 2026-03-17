#!/usr/bin/env python3

from __future__ import annotations

import argparse
import multiprocessing
import shutil
import stat
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> int:
    print(f"$ {' '.join(cmd)}", flush=True)
    completed = subprocess.run(cmd, cwd=cwd, check=False)
    if check and completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return completed.returncode


def capture(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
    )


def output_lines(cmd: list[str]) -> list[str]:
    completed = capture(cmd)
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def ensure_repo_source(llama_cpp_dir: Path, refresh: bool) -> None:
    git_dir = llama_cpp_dir / ".git"
    if git_dir.exists():
        if refresh:
            code = run(
                ["git", "-C", str(llama_cpp_dir), "pull", "--ff-only"],
                check=False,
            )
            if code != 0:
                print("git pull failed, continuing with the existing llama.cpp checkout.", flush=True)
        return

    if llama_cpp_dir.exists():
        shutil.rmtree(llama_cpp_dir)

    llama_cpp_dir.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "https://github.com/ggml-org/llama.cpp.git",
            str(llama_cpp_dir),
        ]
    )


def probe_works(binary: Path) -> bool:
    if not binary.exists():
        return False
    try:
        result = capture([str(binary), "--help"])
    except OSError:
        return False
    merged = f"{result.stdout}\n{result.stderr}".lower()
    return result.returncode == 0 or "usage" in merged or "options" in merged


def repo_has_converter(llama_cpp_dir: Path) -> bool:
    return any(
        (llama_cpp_dir / name).exists()
        for name in ("convert-hf-to-gguf.py", "convert_hf_to_gguf.py")
    )


def root_binary_candidates(llama_cpp_dir: Path, name: str) -> list[Path]:
    if sys.platform == "win32":
        return [
            llama_cpp_dir / f"{name}.exe",
            llama_cpp_dir / "build" / "bin" / "Release" / f"{name}.exe",
            llama_cpp_dir / "build" / "bin" / f"{name}.exe",
        ]
    return [
        llama_cpp_dir / name,
        llama_cpp_dir / "build" / "bin" / name,
    ]


def existing_binary(llama_cpp_dir: Path, name: str) -> Path | None:
    for candidate in root_binary_candidates(llama_cpp_dir, name):
        if candidate.exists():
            return candidate
    return None


def working_install_exists(llama_cpp_dir: Path) -> bool:
    if not repo_has_converter(llama_cpp_dir):
        return False
    server = existing_binary(llama_cpp_dir, "llama-server")
    quantize = existing_binary(llama_cpp_dir, "llama-quantize")
    return (
        server is not None
        and quantize is not None
        and probe_works(server)
        and probe_works(quantize)
    )


def conda_executable() -> str | None:
    return shutil.which("conda")


def install_conda_package(prefix_dir: Path, refresh: bool) -> bool:
    conda = conda_executable()
    if not conda:
        print("conda not found, falling back to source build.", flush=True)
        return False

    prefix_exists = prefix_dir.exists()
    cmd = [
        conda,
        "install" if prefix_exists else "create",
        "-y",
        "-p",
        str(prefix_dir),
        "-c",
        "conda-forge",
        "llama.cpp",
    ]
    code = run(cmd, check=False)
    if code != 0:
        print("conda-forge install failed, falling back to source build.", flush=True)
        return False

    if refresh and prefix_exists:
        print("Refreshed conda-forge llama.cpp in the existing prefix.", flush=True)
    return True


def prefix_binary_candidates(prefix_dir: Path, name: str) -> list[Path]:
    if sys.platform == "win32":
        return [
            prefix_dir / "Library" / "bin" / f"{name}.exe",
            prefix_dir / "Scripts" / f"{name}.exe",
            prefix_dir / "bin" / f"{name}.exe",
            prefix_dir / f"{name}.exe",
        ]
    return [
        prefix_dir / "bin" / name,
        prefix_dir / name,
    ]


def resolve_prefix_binary(prefix_dir: Path, name: str) -> Path | None:
    for candidate in prefix_binary_candidates(prefix_dir, name):
        if probe_works(candidate):
            return candidate
    return None


def write_unix_wrapper(wrapper_path: Path, target: Path) -> None:
    wrapper_path.write_text(
        "#!/bin/sh\n"
        f'exec "{target}" "$@"\n',
        encoding="utf-8",
    )
    mode = wrapper_path.stat().st_mode
    wrapper_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_unix_shims(llama_cpp_dir: Path, server_bin: Path, quantize_bin: Path) -> None:
    write_unix_wrapper(llama_cpp_dir / "llama-server", server_bin)
    write_unix_wrapper(llama_cpp_dir / "llama-quantize", quantize_bin)


def install_windows_shims(llama_cpp_dir: Path, server_bin: Path, quantize_bin: Path) -> None:
    runtime_dir = server_bin.parent
    for candidate in runtime_dir.glob("*.dll"):
        shutil.copy2(candidate, llama_cpp_dir / candidate.name)
    for candidate in runtime_dir.glob("llama-*.exe"):
        shutil.copy2(candidate, llama_cpp_dir / candidate.name)
    shutil.copy2(server_bin, llama_cpp_dir / server_bin.name)
    shutil.copy2(quantize_bin, llama_cpp_dir / quantize_bin.name)


def install_conda_shims(llama_cpp_dir: Path, prefix_dir: Path) -> bool:
    server_bin = resolve_prefix_binary(prefix_dir, "llama-server")
    quantize_bin = resolve_prefix_binary(prefix_dir, "llama-quantize")
    if not server_bin or not quantize_bin:
        return False

    if sys.platform == "win32":
        install_windows_shims(llama_cpp_dir, server_bin, quantize_bin)
    else:
        install_unix_shims(llama_cpp_dir, server_bin, quantize_bin)

    return working_install_exists(llama_cpp_dir)


def detect_nvcc() -> str | None:
    candidates = [shutil.which("nvcc"), "/usr/local/cuda/bin/nvcc"]
    candidates.extend(
        str(path) for path in sorted(Path("/usr/local").glob("cuda-*/bin/nvcc"))
    )
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def detect_cuda_architectures() -> str | None:
    values: list[str] = []
    for line in output_lines(
        ["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"]
    ):
        major, dot, minor = line.partition(".")
        if major.isdigit() and dot and minor.isdigit():
            arch = f"{major}{minor}"
            if arch not in values:
                values.append(arch)
    return ";".join(values) if values else None


def configure_args(llama_cpp_dir: Path) -> list[str]:
    build_dir = llama_cpp_dir / "build"
    args = [
        "cmake",
        "-S",
        str(llama_cpp_dir),
        "-B",
        str(build_dir),
        "-DBUILD_SHARED_LIBS=OFF",
        "-DLLAMA_BUILD_TESTS=OFF",
        "-DLLAMA_BUILD_EXAMPLES=OFF",
        "-DLLAMA_BUILD_SERVER=ON",
        "-DGGML_NATIVE=ON",
    ]
    if shutil.which("ninja"):
        args.extend(["-G", "Ninja"])

    nvcc = detect_nvcc()
    if nvcc:
        args.append("-DGGML_CUDA=ON")
        architectures = detect_cuda_architectures()
        if architectures:
            args.append(f"-DCMAKE_CUDA_ARCHITECTURES={architectures}")

    return args


def ensure_build_prerequisites() -> None:
    missing = [name for name in ("git", "cmake") if shutil.which(name) is None]
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(
            f"Missing required build tool(s): {joined}. Install them and rerun the launcher."
        )


def build_from_source(llama_cpp_dir: Path) -> None:
    ensure_build_prerequisites()
    run(configure_args(llama_cpp_dir))

    jobs = str(max(multiprocessing.cpu_count(), 1))
    build_dir = llama_cpp_dir / "build"
    run(
        [
            "cmake",
            "--build",
            str(build_dir),
            "--config",
            "Release",
            "--target",
            "llama-server",
            "-j",
            jobs,
        ]
    )
    run(
        [
            "cmake",
            "--build",
            str(build_dir),
            "--config",
            "Release",
            "--target",
            "llama-quantize",
            "-j",
            jobs,
        ],
        check=False,
    )

    server_bin = existing_binary(llama_cpp_dir, "llama-server")
    quantize_bin = existing_binary(llama_cpp_dir, "llama-quantize")
    if not server_bin or not quantize_bin:
        raise SystemExit(
            "llama.cpp build finished but llama-server or llama-quantize was not found."
        )

    if sys.platform == "win32":
        build_release_dir = llama_cpp_dir / "build" / "bin" / "Release"
        if build_release_dir.exists():
            for candidate in build_release_dir.glob("*.dll"):
                shutil.copy2(candidate, llama_cpp_dir / candidate.name)
    else:
        install_unix_shims(llama_cpp_dir, server_bin, quantize_bin)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--skip-if-present", action="store_true")
    args = parser.parse_args()

    llama_cpp_dir = Path.home() / ".unsloth" / "llama.cpp"
    prefix_dir = Path.home() / ".unsloth" / "llama-cpp-env"

    if args.skip_if_present and working_install_exists(llama_cpp_dir):
        server = existing_binary(llama_cpp_dir, "llama-server")
        print(f"llama-server already available at {server}", flush=True)
        return

    ensure_repo_source(llama_cpp_dir, refresh=args.refresh)

    conda_ready = install_conda_package(prefix_dir, refresh=args.refresh)
    if conda_ready and install_conda_shims(llama_cpp_dir, prefix_dir):
        server = existing_binary(llama_cpp_dir, "llama-server")
        print(f"llama-server ready via conda-forge at {server}", flush=True)
        return

    print("Falling back to source build for llama.cpp.", flush=True)
    build_from_source(llama_cpp_dir)

    if not working_install_exists(llama_cpp_dir):
        raise SystemExit("llama.cpp setup completed but the resulting install is not usable.")

    server = existing_binary(llama_cpp_dir, "llama-server")
    print(f"llama-server built at {server}", flush=True)


if __name__ == "__main__":
    main()
