# -*- coding: utf-8 -*-
"""
Автообновление релиза (exe): проверка GitHub Releases, скачивание, замена только exe.
Данные пользователя, пакеты .siq и настройки не трогаются.
"""

from __future__ import annotations

import json
import os
import sys
import time
import tempfile
import subprocess
import urllib.request
from typing import Optional, Tuple

from version import __version__
from constants import (
    UPDATE_GITHUB_REPO,
    UPDATE_ASSET_WIN,
    UPDATE_ASSET_LINUX,
    UPDATE_ASSET_MAC,
)


def current_version() -> str:
    return __version__


def _http_json(url: str, timeout: int = 12) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SiPak-Updater/%s" % __version__,
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse_ver(s: str) -> Tuple[int, ...]:
    s = (s or "").strip().lstrip("vV")
    parts = []
    for p in s.split("."):
        num = ""
        for c in p:
            if c.isdigit():
                num += c
            else:
                break
        parts.append(int(num) if num else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:4])


def is_newer(remote: str, local: str) -> bool:
    try:
        return _parse_ver(remote) > _parse_ver(local)
    except Exception:
        return False


def _asset_name() -> str:
    if sys.platform == "win32":
        return UPDATE_ASSET_WIN
    if sys.platform == "darwin":
        return UPDATE_ASSET_MAC
    return UPDATE_ASSET_LINUX


def _skip_path() -> str:
    try:
        from siq_io import user_data_dir

        return os.path.join(user_data_dir(), "skip_version.txt")
    except Exception:
        return os.path.join(tempfile.gettempdir(), "sipak_skip_version.txt")


def get_skipped_version() -> str:
    try:
        p = _skip_path()
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""


def set_skipped_version(ver: str) -> None:
    try:
        with open(_skip_path(), "w", encoding="utf-8") as f:
            f.write((ver or "").strip())
    except Exception:
        pass


def clear_skipped_if_installed(ver: str) -> None:
    if get_skipped_version() == (ver or "").strip():
        try:
            os.remove(_skip_path())
        except Exception:
            pass


def check_github_release(repo: str = "") -> Optional[dict]:
    """
    Только релиз с exe/бинарником.
    up_to_date / error / данные обновления.
    """
    repo = (repo or UPDATE_GITHUB_REPO or "").strip()
    if not repo or "/" not in repo:
        return {"error": "no_repo", "up_to_date": True}

    url = "https://api.github.com/repos/%s/releases/latest" % repo
    try:
        data = _http_json(url)
    except Exception as e:
        return {"error": str(e), "up_to_date": True}

    tag = (data.get("tag_name") or data.get("name") or "").strip()
    ver = tag.lstrip("vV")
    if not ver:
        return {"error": "no_tag", "up_to_date": True}

    if not is_newer(ver, __version__):
        return {
            "up_to_date": True,
            "version": ver,
            "tag": tag,
            "html_url": data.get("html_url") or "",
        }

    asset_want = _asset_name().lower()
    download_url = ""
    asset_size = 0
    for a in data.get("assets") or []:
        name = (a.get("name") or "").lower()
        if name == asset_want or name.endswith("/" + asset_want):
            download_url = a.get("browser_download_url") or ""
            asset_size = int(a.get("size") or 0)
            break
        # допускаем SiPak-windows.exe и т.п.
        if asset_want.replace(".exe", "") in name and (
            name.endswith(".exe") or sys.platform != "win32"
        ):
            download_url = a.get("browser_download_url") or ""
            asset_size = int(a.get("size") or 0)
            break

    if not download_url:
        return {
            "error": "no_exe_asset",
            "up_to_date": True,
            "version": ver,
            "html_url": data.get("html_url") or "",
        }

    return {
        "up_to_date": False,
        "version": ver,
        "tag": tag,
        "notes": (data.get("body") or "")[:1500],
        "download_url": download_url,
        "html_url": data.get("html_url") or "",
        "asset_name": _asset_name(),
        "asset_size": asset_size,
    }


def download_file(url: str, dest: str, timeout: int = 180) -> None:
    req = urllib.request.Request(
        url, headers={"User-Agent": "SiPak-Updater/%s" % __version__}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    if len(data) < 1024:
        raise ValueError("Файл обновления слишком маленький")
    with open(dest, "wb") as f:
        f.write(data)


def exe_target_path() -> str:
    """Путь к файлу программы, который заменяем (только он)."""
    if getattr(sys, "frozen", False):
        return os.path.abspath(sys.executable)
    from siq_io import user_data_dir

    return os.path.abspath(os.path.join(user_data_dir(), _asset_name()))


def install_exe_update(download_url: str) -> Tuple[bool, str]:
    """
    Скачивает новый бинарник и планирует замену ТОЛЬКО exe после выхода.
    Папки с .siq, настройки, временные медиа — не удаляются.
    """
    try:
        target = exe_target_path()
        folder = os.path.dirname(target)
        os.makedirs(folder, exist_ok=True)

        tmp = target + ".new"
        bak = target + ".bak"
        download_file(download_url, tmp)

        if sys.platform == "win32":
            bat = os.path.join(folder, "_sipak_update.bat")
            # ждём пока exe освободится, move .new → exe, старый → .bak (на всякий), старт
            script = (
                "@echo off\r\n"
                "set TARGET=%s\r\n"
                "set NEW=%s\r\n"
                "set BAK=%s\r\n"
                "set /a n=0\r\n"
                ":wait\r\n"
                "ping 127.0.0.1 -n 2 >nul\r\n"
                "set /a n+=1\r\n"
                'if exist "%%TARGET%%" (\r\n'
                '  del /F /Q "%%BAK%%" 2>nul\r\n'
                '  ren "%%TARGET%%" "%s" 2>nul\r\n'
                ")\r\n"
                'if exist "%%TARGET%%" if %%n%% LSS 30 goto wait\r\n'
                'move /Y "%%NEW%%" "%%TARGET%%"\r\n'
                'if not exist "%%TARGET%%" (\r\n'
                '  if exist "%%BAK%%" ren "%%BAK%%" "%s"\r\n'
                "  exit /b 1\r\n"
                ")\r\n"
                'start "" "%%TARGET%%"\r\n'
                'del "%%BAK%%" 2>nul\r\n'
                'del "%%~f0"\r\n'
            ) % (
                target,
                tmp,
                bak,
                os.path.basename(bak),
                os.path.basename(target),
            )
            with open(bat, "w", encoding="cp866", errors="replace") as f:
                f.write(script)
            subprocess.Popen(
                ["cmd", "/c", bat],
                cwd=folder,
                close_fds=True,
                creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
            return True, "Обновление готово. Программа перезапустится с новой версией."

        # Linux / macOS
        os.chmod(tmp, 0o755)
        if os.path.isfile(target):
            try:
                if os.path.isfile(bak):
                    os.remove(bak)
                os.replace(target, bak)
            except OSError:
                pass
        os.replace(tmp, target)
        try:
            if os.path.isfile(bak):
                os.remove(bak)
        except OSError:
            pass
        return True, "Файл программы обновлён. Перезапустите СиПак."
    except Exception as e:
        return False, str(e)


def check_git_update(project_dir: str) -> Optional[dict]:
    git_dir = os.path.join(project_dir, ".git")
    if not os.path.isdir(git_dir):
        return None
    try:
        subprocess.run(
            ["git", "-C", project_dir, "fetch", "--quiet"],
            check=False,
            timeout=45,
            capture_output=True,
        )
        local = subprocess.check_output(
            ["git", "-C", project_dir, "rev-parse", "HEAD"],
            text=True,
            timeout=15,
        ).strip()
        remote = subprocess.check_output(
            ["git", "-C", project_dir, "rev-parse", "@{u}"],
            text=True,
            timeout=15,
            stderr=subprocess.DEVNULL,
        ).strip()
        if local != remote:
            return {
                "up_to_date": False,
                "kind": "git",
                "local": local[:8],
                "remote": remote[:8],
                "project_dir": project_dir,
            }
        return {"up_to_date": True, "kind": "git"}
    except Exception as e:
        return {"error": str(e), "kind": "git"}


def git_pull(project_dir: str) -> Tuple[bool, str]:
    try:
        r = subprocess.run(
            ["git", "-C", project_dir, "pull", "--ff-only"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode == 0:
            return True, (r.stdout or "OK").strip()
        return False, (r.stderr or r.stdout or "git pull failed").strip()
    except Exception as e:
        return False, str(e)


def install_zip_source(download_url: str, project_dir: str) -> Tuple[bool, str]:
    import zipfile
    import shutil

    try:
        td = tempfile.mkdtemp(prefix="sipak_upd_")
        zpath = os.path.join(td, "src.zip")
        download_file(download_url, zpath)
        with zipfile.ZipFile(zpath, "r") as zf:
            zf.extractall(td)
        root = None
        for name in os.listdir(td):
            full = os.path.join(td, name)
            if os.path.isdir(full) and name != "__MACOSX":
                root = full
                break
        if not root:
            return False, "В архиве нет папки с кодом"
        for dirpath, _, files in os.walk(root):
            rel = os.path.relpath(dirpath, root)
            dest_dir = os.path.join(project_dir, rel) if rel != "." else project_dir
            os.makedirs(dest_dir, exist_ok=True)
            for fn in files:
                if fn.endswith((".pyc", ".pyo")):
                    continue
                shutil.copy2(os.path.join(dirpath, fn), os.path.join(dest_dir, fn))
        shutil.rmtree(td, ignore_errors=True)
        return True, "Исходники обновлены. Перезапустите программу."
    except Exception as e:
        return False, str(e)
