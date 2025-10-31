# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Wrapper script that preserves progress callbacks for subprocess job submission."""

import sys
import json
from deadline.client.api import create_job_from_job_bundle


def hash_progress_callback(hash_metadata):
    print(
        json.dumps(
            {
                "type": "hash_progress",
                "progress": hash_metadata.progress,
                "message": hash_metadata.progressMessage,
            }
        ),
        flush=True,
    )
    # Always return True in subprocess - cancellation handled by parent
    return True


def upload_progress_callback(upload_metadata):
    print(
        json.dumps(
            {
                "type": "upload_progress",
                "progress": upload_metadata.progress,
                "message": upload_metadata.progressMessage,
            }
        ),
        flush=True,
    )
    # Always return True in subprocess - cancellation handled by parent
    return True


def create_job_result_callback():
    print(json.dumps({"type": "create_job_result"}), flush=True)
    return True


def print_function_callback(message):
    """Capture print messages from the API"""
    print(json.dumps({"type": "api_message", "message": message}), flush=True)


def interactive_confirmation_callback(message, default_response):
    """Always accept confirmations in subprocess mode"""
    print(json.dumps({"type": "debug", "message": f"Confirmation prompt: {message}"}), flush=True)
    return True


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(
            json.dumps(
                {
                    "type": "error",
                    "message": "Usage: job_submit_wrapper.py <job_bundle_path> [known_asset_path]",
                }
            )
        )
        sys.exit(1)

    job_bundle_path = sys.argv[1]
    known_asset_path = sys.argv[2] if len(sys.argv) == 3 else None

    try:
        print(
            json.dumps(
                {
                    "type": "debug",
                    "message": f"Starting job creation with bundle: {job_bundle_path}",
                }
            ),
            flush=True,
        )
        if known_asset_path:
            print(
                json.dumps(
                    {"type": "debug", "message": f"Using known asset path: {known_asset_path}"}
                ),
                flush=True,
            )

        job_id = create_job_from_job_bundle(
            job_bundle_dir=job_bundle_path,
            hashing_progress_callback=hash_progress_callback,
            upload_progress_callback=upload_progress_callback,
            create_job_result_callback=create_job_result_callback,
            interactive_confirmation_callback=interactive_confirmation_callback,
            print_function_callback=print_function_callback,
            from_gui=False,
            known_asset_paths=[known_asset_path] if known_asset_path else None,  # type: ignore[arg-type]
        )
        print(json.dumps({"type": "job_created", "job_id": job_id}), flush=True)
    except Exception as e:
        import traceback

        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(json.dumps({"type": "error", "message": error_msg}), flush=True)
        # Also print to stderr for additional debugging
        print(f"ERROR: {error_msg}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
