import json
import sys
import threading

from pathlib import Path

from app.export_job import ExportJob
from app.export_worker import CropExportWorker


def main():
    if len(sys.argv) != 2:
        print(
            "ExportJob JSON file path is required",
            file=sys.stderr,
        )
        return 2

    job_file_path = Path(
        sys.argv[1]
    )

    try:
        json_text = job_file_path.read_text(
            encoding="utf-8"
        )

        export_job = ExportJob.from_json(
            json_text
        )

        export_worker = CropExportWorker(
            export_job
        )

        def listen_for_commands():
            while True:
                command = sys.stdin.readline()

                if not command:
                    return

                command = command.strip().lower()

                if command == "stop":
                    export_worker.request_stop()
                    return

        command_thread = threading.Thread(
            target=listen_for_commands,
            daemon=True,
        )

        command_thread.start()

        def send_progress(
            value,
            saved_count,
            total_crops,
        ):
            progress_result = {
                "status": "progress",
                "value": int(
                    value
                ),
                "saved_count": int(
                    saved_count
                ),
                "total_crops": int(
                    total_crops
                ),
            }

            print(
                json.dumps(
                    progress_result,
                    ensure_ascii=False,
                ),
                flush=True,
            )

        export_worker.progress.connect(
            send_progress
        )

        saved_count = (
            export_worker.export_images()
        )

        if export_worker.stop_requested:
            result = {
                "status": "stopped",
                "saved_count": int(
                    saved_count
                ),
            }

        else:
            result = {
                "status": "finished",
                "saved_count": int(
                    saved_count
                ),
            }

        print(
            json.dumps(
                result,
                ensure_ascii=False,
            ),
            flush=True,
        )

        return 0

    except Exception as e:
        result = {
            "status": "failed",
            "message": str(e),
        }

        print(
            json.dumps(
                result,
                ensure_ascii=False,
            ),
            file=sys.stderr,
            flush=True,
        )

        return 1


if __name__ == "__main__":
    sys.exit(
        main()
    )