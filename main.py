#!/usr/bin/env python3
# Copyright (c) 2026, Mark LaPointe <mark@cloudbsd.org>
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import os
import sys
import time
import concurrent.futures
from pathlib import Path

from utils import format_size, get_file_size, parse_m3u
from tui import tui_select
from download_manager import DownloadManager
from downloader import download_file
from m3utolocal.cli_args import parse_args
from m3utolocal.domain.match import find_matches
from m3utolocal.domain.job_builder import build_jobs
from m3utolocal.services.config import load_settings
from m3utolocal.services.cleanup import CleanupService, CleanupPolicy
from m3utolocal.i18n import LocaleService, set_language


def main(argv=None):
    args = parse_args(argv)

    try:
        settings = load_settings(
            cli_overrides={
                "m3u_path": getattr(args, "m3u", None),
                "threads": getattr(args, "threads", None),
                "retries": getattr(args, "retries", None),
                "output_dir": getattr(args, "output", None),
                "language": getattr(args, "lang", None),
            }
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    locale = LocaleService()
    lang = locale.detect(
        cli_lang=getattr(args, "lang", None),
        config_lang=settings.language,
    )
    set_language(lang)

    if args.command == "init":
        from m3utolocal.services.config import write_config_template
        path = write_config_template()
        print(f"Wrote config: {path}")
        return

    if args.command == "cleanup":
        out = (
            Path(args.output)
            if getattr(args, "output", None) and args.output
            else settings.resolved_output_dir()
        )
        svc = CleanupService()
        if getattr(args, "migrate_cwd", False):
            dry = not getattr(args, "apply", False)
            moves = svc.migrate_cwd_media(Path.cwd(), out, dry_run=dry)
            for src, dst in moves:
                print(f"{'Would move' if dry else 'Moved'}: {src} -> {dst}")
            print(f"{len(moves)} file(s).")
            return
        policy = CleanupPolicy(
            include_empty=not getattr(args, "parts_only", False),
            include_orphan_temps=not getattr(args, "parts_only", False),
        )
        plan = svc.plan(out, policy=policy)
        for item in plan.items:
            print(f"[{item.kind}] {item.path} ({item.size} bytes) — {item.reason}")
        dry = not getattr(args, "apply", False)
        result = svc.execute(plan, dry_run=dry)
        print(
            f"{'Planned' if dry else 'Removed'}: {result['planned']} items "
            f"({result.get('bytes_freed', 0)} bytes freed if applied)."
        )
        return

    # Interactive full-screen TUI:
    #  - no query and not -y  → home TUI
    #  - query + --tui (and not -y) → search TUI pre-filled
    #  - no query but -m only → home TUI (default PyCharm case)
    want_tui = not args.yes and (
        args.query is None or getattr(args, "tui", False)
    )
    if want_tui and args.query is None:
        try:
            from m3utolocal.ui.app import run_tui
        except ImportError:
            print(
                "Error: Textual is required for the TUI. "
                "Install py-textual / textual."
            )
            sys.exit(1)
        run_tui(settings, initial_query=None)
        return

    if not args.query:
        print(
            "Error: query is required for headless mode (-y); "
            "omit query (optionally pass -m PLAYLIST) to open the TUI."
        )
        sys.exit(1)

    search_query = args.query
    m3u_file = settings.m3u_path
    download_dir = settings.resolved_output_dir()

    if not os.path.exists(m3u_file):
        print(f"Error: {m3u_file} not found.")
        sys.exit(1)

    # Optional Textual search pre-filled with query (interactive, not -y)
    if not args.yes and getattr(args, "tui", False):
        try:
            from m3utolocal.ui.app import run_tui
        except ImportError:
            print("Error: Textual is required for the TUI.")
            sys.exit(1)
        run_tui(settings, initial_query=search_query)
        return

    print(f"Searching for '{search_query}' in '{m3u_file}'...")
    channels = parse_m3u(m3u_file)
    matches = find_matches(channels, search_query)
    
    if not matches:
        print(f"No non-live matches found for '{search_query}'.")
        return

    # Fetch sizes for all matches to display in selection UI
    print(f"Fetching file sizes for {len(matches)} matches...")
    # ANSI colors for cycling dots
    dot_colors = ["\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[94m", "\033[95m"]
    reset = "\033[0m"
    
    try:
        prev_width = 0
        for i, match in enumerate(matches):
            try:
                columns = os.get_terminal_size().columns
            except OSError:
                columns = 80
            
            if columns != prev_width:
                sys.stdout.write("\033[J") # Clear below if width changed
                prev_width = columns

            num_dots = (i % 3) + 1
            dots = "." * num_dots
            color = dot_colors[i % len(dot_colors)]
            percent = (i / len(matches)) * 100
            # Print with colorful dots, padded to avoid flickering
            print(f"\r[{percent:5.1f}%] Fetching sizes {color}{dots:<3}{reset}", end="", flush=True)
            match['size'] = get_file_size(match['url'])
        print(f"\r[100.0%] Fetching sizes {dot_colors[2]}Done.{reset}             ")
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return

    green = "\033[92m"

    if not args.yes:
        # Prefer full Textual app when available; fall back to curses multi-select
        try:
            from m3utolocal.ui.app import run_tui
            run_tui(settings, initial_query=search_query)
            return
        except ImportError:
            selected_indices = tui_select(matches)
            if selected_indices is None:
                print("Download cancelled.")
                return
    else:
        selected_indices = list(range(len(matches)))

    # Only keep selected matches (curses path / headless)
    matches = [matches[i] for i in selected_indices]
    
    if not matches:
        print("No items selected for download.")
        return

    total_download_size = sum(match.get('size', 0) for match in matches)
    print(f"\nTotal volume to be downloaded: {format_size(total_download_size)}")
    print(f"Output directory: {download_dir}")

    download_dir.mkdir(parents=True, exist_ok=True)

    if args.auto_clean or settings.auto_clean_parts:
        clean_plan = CleanupService().plan(
            download_dir, policy=CleanupPolicy(part_max_age_seconds=0)
        )
        # Only auto-remove zero-byte and orphan temps by default policy ages
        CleanupService().execute(clean_plan, dry_run=False)

    jobs = build_jobs(matches, download_dir)
    print("\nStarting downloads...")
    
    manager = DownloadManager(len(jobs))
    max_retries = settings.retries
    max_threads = settings.threads

    def process_download(job, final=True):
        # Always write under output root (final_path); resume via .part beside it
        download_file(
            job.channel.url,
            str(job.final_path),
            manager=manager,
            file_id=job.id,
            final=final,
        )

    try:
        failed_downloads = []
        current_threads = max_threads
        
        for job in jobs:
            manager.update_progress(
                job.id, job.final_path.name, 0, "0.0 KB/s", "--", status="Queued"
            )

        if current_threads > 1:
            active_futures = {}
            remaining_to_submit = list(jobs)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
                while remaining_to_submit or active_futures:
                    while remaining_to_submit and len(active_futures) < current_threads:
                        job = remaining_to_submit.pop(0)
                        future = executor.submit(process_download, job, False)
                        active_futures[future] = job
                
                    if not active_futures:
                        break
                    
                    done, _ = concurrent.futures.wait(
                        active_futures.keys(),
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )
                
                    for future in done:
                        job = active_futures.pop(future)
                        try:
                            future.result()
                        except (KeyboardInterrupt, SystemExit):
                            raise
                        except Exception:
                            failed_downloads.append(job)
                            if current_threads > 1:
                                current_threads = max(1, current_threads - 1)
        else:
            for job in jobs:
                try:
                    process_download(job, final=True)
                except KeyboardInterrupt:
                    raise
                except Exception:
                    failed_downloads.append(job)

        retry_count = 0
        while failed_downloads and retry_count < max_retries:
            retry_count += 1
            to_retry = list(failed_downloads)
            failed_downloads = []
            
            for job in to_retry:
                time.sleep(1)
                try:
                    is_last_attempt = retry_count == max_retries
                    process_download(job, final=is_last_attempt)
                except KeyboardInterrupt:
                    raise
                except Exception:
                    failed_downloads.append(job)

        if failed_downloads:
            print(f"\n\033[91m{len(failed_downloads)} download(s) failed.\033[0m")
            sys.exit(2)
        print(f"\n{green}All downloads completed.{reset}")
    except KeyboardInterrupt:
        print("\nDownload cancelled by user.")
        sys.exit(130)

if __name__ == "__main__":
    main()
