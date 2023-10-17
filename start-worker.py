import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from rich import inspect

cwd = Path(__file__).parent.absolute()
os.chdir(cwd)

sys.path.append(str(cwd / "src"))

host = "localhost"
redis_url = f"redis://{host}:7300"

subprocess.run(
    ["docker", "compose", "--file", str(cwd / "deploy" / "dev.docker-compose.yaml"), "up", "--detach"], check=True
)

rq_process = subprocess.Popen(
    [shutil.which("rq"), "worker", "--with-scheduler", "--url", redis_url, "--verbose", "tasker"],
    env={"PYTHONPATH": os.pathsep.join([os.environ.get("PYTHONPATH", ""), str(cwd / "src")]), "DEBUG_MODE": "on"},
)
rq_dashboard_process = subprocess.Popen([shutil.which("rq-dashboard"), "--redis-url", redis_url, "--port", "7400"])


def stop_subprocesses(signum, frame) -> None:
    def stop_process(process: subprocess.Popen) -> None:
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    inspect(signum)
    inspect(frame)
    stop_process(rq_process)
    stop_process(rq_dashboard_process)


signal.signal(signal.SIGINT, stop_subprocesses)

rq_process.wait()
rq_dashboard_process.wait()
