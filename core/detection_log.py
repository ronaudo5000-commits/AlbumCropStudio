from datetime import datetime
import os
from pathlib import Path
import platform
import threading


LOG_MAX_BYTES = 5 * 1024 * 1024


def get_detection_log_path():
    log_dir = (
        Path.home()
        / ".albumcrop_studio"
        / "logs"
    )

    log_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return (
        log_dir
        / "detection.log"
    )


def rotate_detection_log_if_needed(
    log_path,
):
    try:
        if not log_path.exists():
            return

        if log_path.stat().st_size < LOG_MAX_BYTES:
            return

        backup_path = log_path.with_name(
            "detection.log.1"
        )

        if backup_path.exists():
            backup_path.unlink()

        log_path.replace(
            backup_path
        )

    except Exception:
        # 診断ログの失敗によって
        # 本体処理を止めない
        pass


def write_detection_log(message):
    try:
        log_path = (
            get_detection_log_path()
        )

        rotate_detection_log_if_needed(
            log_path
        )

        timestamp = (
            datetime.now().astimezone()
            .isoformat(
                timespec="milliseconds"
            )
        )

        process_id = os.getpid()

        thread_id = threading.get_ident()

        line = (
            f"{timestamp} "
            f"[pid={process_id}] "
            f"[thread={thread_id}] "
            f"{message}\n"
        )

        with log_path.open(
            "a",
            encoding="utf-8",
        ) as log_file:
            log_file.write(
                line
            )

    except Exception:
        # ログ機能自体の不具合で
        # ACSの処理を止めない
        pass


def write_detection_environment():
    try:
        write_detection_log(
            "environment "
            f"os={platform.platform()} "
            f"python={platform.python_version()}"
        )

    except Exception:
        pass