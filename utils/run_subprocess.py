import os
import subprocess

def exec_cmd(cmd, inp=None):
    try:
        result = subprocess.run(
            cmd,
            check=True,
            text=True,
            input=inp,
            shell=os.name == "nt",
            capture_output=True,
            timeout=120, # Increased timeout for Windows
        )
        if result is not None:
            result = result.stdout.strip()
        # print("CMD result:", result)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error executing command {cmd}: {e.stderr}")
        print("Output:", e.stdout)
        return None
    except subprocess.TimeoutExpired as e:
        print(f"Command timed out {cmd} after {e.timeout} seconds")
        if e.stdout: print("Output so far:", e.stdout.decode())
        if e.stderr: print("Error so far:", e.stderr.decode())
        return None
    except Exception as e:
        print(f"Unexpected error executing {cmd}: {e}")
        return None


def pop_cmd(cmd, cwd=None):
    """
    Run a command and stream stdout/stderr, with OS-specific handling.

    - On Windows (os.name == "nt"), we run through the shell with a string.
    - On POSIX systems, we pass a list directly with shell=False.
    - If the Docker engine is not reachable on Windows, we surface a clear error.
    - cwd: optional working directory for the subprocess.
    """
    is_windows = os.name == "nt"

    # Normalize command into both a display string and an argument list.
    if isinstance(cmd, (list, tuple)):
        args_list = [str(c) for c in cmd]
    else:
        args_list = [str(cmd)]
    display_cmd = " ".join(args_list)

    popen_kw = dict(
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if cwd is not None:
        popen_kw["cwd"] = cwd

    try:
        if is_windows:
            # Windows: use the shell with a single string.
            process = subprocess.Popen(
                display_cmd,
                shell=True,
                **popen_kw,
            )
        else:
            # POSIX: avoid shell, pass the argument list directly.
            process = subprocess.Popen(
                args_list,
                shell=False,
                **popen_kw,
            )

        output_lines = []
        for line in process.stdout:
            output_lines.append(line)
            print(line, end="")

        process.wait()

        if process.returncode != 0:
            combined_output = "".join(output_lines)

            # Special-case: Docker Desktop engine not running on Windows.
            if is_windows and "dockerDesktopLinuxEngine" in combined_output:
                raise RuntimeError(
                    "Docker engine is not running. Please start Docker Desktop "
                    "and ensure the Linux engine is enabled, then retry.\n"
                    f"Command: {display_cmd}"
                )

            raise RuntimeError(
                f"Command failed with exit code {process.returncode}: {display_cmd}"
            )
    except FileNotFoundError as e:
        # Command itself not found (e.g. 'docker' or 'gcloud' missing).
        raise RuntimeError(
            f"Command not found: {args_list[0]}. "
            "Is it installed and on your PATH?"
        ) from e