import os
import sys
import time

import requests

from utils import format_time


def download_file(
    url,
    target_filename,
    manager=None,
    file_id=None,
    final=True,
    session=None,
    on_progress=None,
):
    """Download *url* to *target_filename* with resume support.

    Uses HEAD (when possible) for metadata, then a single body GET.
    Partial data is written to ``target_filename + ".part"`` and renamed on success.

    Resume rules:
      - If ``.part`` size equals remote size → finalize (rename), no re-download.
      - If ``.part`` is smaller → send ``Range: bytes=N-`` when possible.
      - If server answers **206**, append to ``.part``.
      - If server answers **200** (ignored Range), truncate and rewrite cleanly
        (never append a full body onto an existing partial — that corrupts data).
      - If ``.part`` is larger than remote size → discard and restart.

    *on_progress* is an optional callable::

        on_progress(downloaded: int, total_size: int, rate_str: str, eta_str: str) -> None
    """
    display_name = os.path.basename(target_filename)
    rate_str = "0.0 KB/s"
    http = session or requests
    req_headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) VLC/3.0.18"}
    try:
        total_size = 0
        accept_ranges = False
        try:
            head = http.head(url, allow_redirects=True, headers=req_headers, timeout=30)
            if head.status_code < 400:
                total_size = int(head.headers.get("content-length", 0) or 0)
                ar = head.headers.get("Accept-Ranges") or head.headers.get("accept-ranges") or ""
                accept_ranges = ar.lower() == "bytes" or "bytes" in ar.lower()
                if total_size == 0:
                    cr = head.headers.get("content-range") or head.headers.get("Content-Range") or ""
                    if "/" in cr:
                        try:
                            total_size = int(cr.split("/")[-1])
                        except ValueError:
                            pass
        except Exception:
            pass

        if total_size == 0:
            try:
                with http.get(url, headers=req_headers, stream=True, timeout=30) as probe:
                    if probe.status_code < 400:
                        total_size = int(probe.headers.get("content-length", 0) or 0)
                        ar = (
                            probe.headers.get("Accept-Ranges")
                            or probe.headers.get("accept-ranges")
                            or ""
                        )
                        accept_ranges = ar.lower() == "bytes" or "bytes" in ar.lower()
                        if total_size == 0:
                            cr = (
                                probe.headers.get("content-range")
                                or probe.headers.get("Content-Range")
                                or ""
                            )
                            if "/" in cr:
                                try:
                                    total_size = int(cr.split("/")[-1])
                                except ValueError:
                                    pass
            except Exception:
                pass

        # Completed final file
        if os.path.exists(target_filename):
            local_size = os.path.getsize(target_filename)
            if total_size > 0 and local_size == total_size:
                if on_progress:
                    on_progress(total_size, total_size, "0.0 KB/s", "ETA: Done")
                if manager:
                    manager.complete_download(file_id, display_name, "Skipped", final=final)
                else:
                    magenta = "\033[95m"
                    reset = "\033[0m"
                    print(
                        f"{magenta}File '{target_filename}' already exists "
                        f"and size matches. Skipping.{reset}"
                    )
                return
            if not manager:
                print(
                    f"File '{target_filename}' exists but size mismatch "
                    f"(Local: {local_size}, Remote: {total_size}). Redownloading..."
                )

        temp_path = target_filename + ".part"
        initial_pos = 0
        try_resume = False

        if os.path.exists(temp_path):
            initial_pos = os.path.getsize(temp_path)
            if total_size > 0 and initial_pos == total_size:
                # Complete partial — finalize without another GET
                if os.path.exists(target_filename):
                    os.remove(target_filename)
                os.rename(temp_path, target_filename)
                if on_progress:
                    on_progress(total_size, total_size, "0.0 KB/s", "ETA: Done")
                if manager:
                    manager.complete_download(
                        file_id, display_name, "0.0 KB/s", final=final
                    )
                elif not on_progress:
                    green = "\033[92m"
                    reset = "\033[0m"
                    print(
                        f"{green}Recovered complete partial "
                        f"'{target_filename}'.{reset}"
                    )
                return
            if total_size > 0 and initial_pos > total_size:
                # Corrupt / oversized partial
                if not manager:
                    print(
                        f"Partial '{temp_path}' is larger than remote "
                        f"({initial_pos} > {total_size}); restarting."
                    )
                os.remove(temp_path)
                initial_pos = 0
            elif initial_pos > 0 and (total_size == 0 or initial_pos < total_size):
                # Always attempt Range when we have progress; many CDNs omit
                # Accept-Ranges on HEAD but still honor Range on GET.
                try_resume = True

        if not manager:
            print(f"Downloading to '{target_filename}' ({total_size} bytes)...")
            if try_resume and initial_pos > 0:
                print(f"Resuming from byte {initial_pos}...")

        headers = dict(req_headers)
        if try_resume and initial_pos > 0:
            headers["Range"] = f"bytes={initial_pos}-"

        response = http.get(url, headers=headers, stream=True, timeout=30)
        try:
            # Some servers return 416 if Range is past EOF — restart clean
            if response.status_code == 416 and try_resume:
                response.close()
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                initial_pos = 0
                try_resume = False
                headers = dict(req_headers)
                response = http.get(url, headers=headers, stream=True, timeout=30)

            with response:
                response.raise_for_status()
                r = response

                # Infer total size from this response if still unknown
                if total_size == 0:
                    cr = (
                        r.headers.get("content-range")
                        or r.headers.get("Content-Range")
                        or ""
                    )
                    if "/" in cr:
                        try:
                            total_size = int(cr.split("/")[-1])
                        except ValueError:
                            pass
                    if total_size == 0:
                        cl = int(r.headers.get("content-length", 0) or 0)
                        if r.status_code == 206 and initial_pos > 0:
                            total_size = initial_pos + cl
                        else:
                            total_size = cl

                # Decide append vs rewrite based on status code
                if try_resume and initial_pos > 0:
                    if r.status_code == 206:
                        mode = "ab"
                        downloaded_start = initial_pos
                    elif r.status_code == 200:
                        # Server ignored Range — do not append (would corrupt)
                        if not manager:
                            print(
                                "Server ignored Range request; "
                                "restarting download from byte 0."
                            )
                        mode = "wb"
                        downloaded_start = 0
                        initial_pos = 0
                    else:
                        r.raise_for_status()
                        mode = "wb"
                        downloaded_start = 0
                else:
                    mode = "wb"
                    downloaded_start = 0

                return _write_body(
                    r,
                    temp_path=temp_path,
                    target_filename=target_filename,
                    mode=mode,
                    downloaded_start=downloaded_start,
                    total_size=total_size,
                    manager=manager,
                    file_id=file_id,
                    final=final,
                    on_progress=on_progress,
                    display_name=display_name,
                )
        except Exception:
            response.close()
            raise

    except KeyboardInterrupt:
        raise
    except Exception as e:
        if manager:
            manager.complete_download(
                file_id, display_name, "0.0 KB/s", error=str(e), final=final
            )
        else:
            print(f"\nFailed to download '{url}': {e}")
        raise


def _write_body(
    r,
    *,
    temp_path,
    target_filename,
    mode,
    downloaded_start,
    total_size,
    manager,
    file_id,
    final,
    on_progress,
    display_name,
):
    rate_str = "0.0 KB/s"
    with open(temp_path, mode) as tmp_file:
        downloaded = downloaded_start
        start_time = time.time()
        last_update_time = start_time
        downloaded_since_start = 0
        rate = 0.0

        try:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                tmp_file.write(chunk)
                downloaded += len(chunk)
                downloaded_since_start += len(chunk)

                current_time = time.time()
                if (
                    current_time - last_update_time < 0.1
                    and total_size > 0
                    and downloaded != total_size
                ):
                    continue

                try:
                    columns = os.get_terminal_size().columns
                except OSError:
                    columns = 80

                if not hasattr(download_file, "prev_width"):
                    download_file.prev_width = columns
                if columns != download_file.prev_width:
                    sys.stdout.write("\033[J")
                    download_file.prev_width = columns

                percent = 0.0
                eta_str = "ETA: --"
                elapsed = current_time - start_time
                if elapsed > 0:
                    rate = downloaded_since_start / elapsed
                    if rate > 1024 * 1024:
                        rate_str = f"{rate / (1024 * 1024):5.1f} MB/s"
                    else:
                        rate_str = f"{rate / 1024:5.1f} KB/s"
                if total_size > 0:
                    percent = min(100.0, downloaded / total_size * 100)
                    if elapsed > 0 and rate > 0:
                        remaining = max(0, total_size - downloaded)
                        eta_str = f"ETA: {format_time(remaining / rate)}"

                if on_progress:
                    on_progress(downloaded, total_size, rate_str, eta_str)
                if manager:
                    manager.update_progress(
                        file_id, display_name, percent, rate_str, eta_str
                    )
                elif not on_progress:
                    display_name_scrolled = display_name
                    if len(display_name) > 20:
                        offset = int(time.time() * 3) % (len(display_name) + 5)
                        padded_name = display_name + "     "
                        display_name_scrolled = (
                            padded_name[offset:] + padded_name[:offset]
                        )[:20]

                    if percent < 33:
                        color = "\033[91m"
                    elif percent < 66:
                        color = "\033[93m"
                    elif percent < 100:
                        color = "\033[94m"
                    else:
                        color = "\033[92m"
                    reset = "\033[0m"

                    percent_str = f"{percent:6.1f}%"
                    rate_str_fixed = f"{rate_str:>10}"
                    eta_str_fixed = f"{eta_str:<15}"
                    prefix = f"{display_name_scrolled:<20} ["
                    suffix = f"] {percent_str} {rate_str_fixed} {eta_str_fixed}"
                    colored_suffix = (
                        f"] {color}{percent_str}{reset} "
                        f"{rate_str_fixed} {eta_str_fixed}"
                    )
                    bar_width = columns - len(prefix) - len(suffix) - 2
                    if bar_width > 0:
                        full_blocks = int(percent * bar_width / 100)
                        fraction = (percent * bar_width / 100) - full_blocks
                        bar = f"{color}:" * full_blocks
                        if fraction > 0 and full_blocks < bar_width:
                            bar += "."
                            padding = " " * (bar_width - full_blocks - 1)
                        else:
                            padding = " " * (bar_width - full_blocks)
                        sys.stdout.write(
                            f"\r{prefix}{bar}{reset}{padding}{colored_suffix}"
                        )
                        sys.stdout.flush()
                last_update_time = current_time
        except KeyboardInterrupt:
            if manager:
                manager.complete_download(
                    file_id,
                    display_name,
                    "0.0 KB/s",
                    error="Interrupted",
                    final=final,
                )
            raise

    if not manager and not on_progress:
        print()

    if os.path.exists(target_filename):
        os.remove(target_filename)
    os.rename(temp_path, target_filename)

    if on_progress:
        final_total = total_size if total_size > 0 else os.path.getsize(target_filename)
        on_progress(final_total, final_total, rate_str, "ETA: Done")
    if manager:
        manager.complete_download(file_id, display_name, rate_str, final=final)
    elif not on_progress:
        green = "\033[92m"
        reset = "\033[0m"
        print(f"{green}Successfully downloaded '{target_filename}'.{reset}")
