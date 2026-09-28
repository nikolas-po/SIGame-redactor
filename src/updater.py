# -*- coding: utf-8 -*-
"""
Обновление с GitHub Releases: проверка, скачивание, замена exe.
Пакеты .siq и данные пользователя не трогаются.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from typing import Optional, Tuple

from constants import (
    UPDATE_ASSET_LINUX,
    UPDATE_ASSET_MAC,
    UPDATE_ASSET_WIN,
    UPDATE_GITHUB_REPO,
)
from version import __version__


def current_version() -> str:
    return __version__


def normalize_repo(repo: str) -> str:
    """user/repo из строки, URL или git@github.com:..."""
    s = (repo or "").strip()
    if not s:
        return ""
    s = s.replace("\\", "/")
    # https://github.com/user/repo.git
    for prefix in (
        "https://github.com/",
        "http://github.com/",
        "github.com/",
        "git@github.com:",
    ):
        if s.lower().startswith(prefix) or s.startswith(prefix):
            s = s[len(prefix) :] if s.startswith(prefix) else s[len(prefix) :]
            break
    # иногда вставляют полный URL API
    if "api.github.com/repos/" in s.lower():
        idx = s.lower().index("api.github.com/repos/") + len("api.github.com/repos/")
        s = s[idx:]
    s = s.strip("/")
    if s.endswith(".git"):
        s = s[:-4]
    # только user/repo
    parts = [p for p in s.split("/") if p]
    if len(parts) >= 2:
        return parts[0] + "/" + parts[1]
    return ""


def _headers() -> dict:
    h = {
        "User-Agent": "SiPak-Updater/%s" % __version__,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = ""
    try:
        from env_load import get as env_get
        from env_load import load_env

        load_env()
        token = (
            env_get("GITHUB_TOKEN") or env_get("UPDATE_GITHUB_TOKEN") or ""
        ).strip()
    except Exception:
        token = (
            os.environ.get("GITHUB_TOKEN")
            or os.environ.get("UPDATE_GITHUB_TOKEN")
            or ""
        ).strip()
    if token:
        h["Authorization"] = "Bearer " + token
    return h


def _http_json(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        if e.code == 404:
            raise RuntimeError(
                "404: репозиторий или релизы не найдены. "
                "Проверьте имя (user/repo), что репозиторий публичный "
                "и что есть хотя бы один Release на GitHub."
            ) from e
        if e.code == 401 or e.code == 403:
            raise RuntimeError(
                "GitHub отказал в доступе (%s). "
                "Для приватного репо укажите GITHUB_TOKEN в .env" % e.code
            ) from e
        raise RuntimeError("GitHub HTTP %s: %s" % (e.code, body or e.reason)) from e
    except urllib.error.URLError as e:
        raise RuntimeError("Нет сети или GitHub недоступен: %s" % e.reason) from e


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
        return UPDATE_ASSET_WIN or "SiPak.exe"
    if sys.platform == "darwin":
        return UPDATE_ASSET_MAC or "SiPak"
    return UPDATE_ASSET_LINUX or "SiPak"


def _pick_asset(assets: list) -> Tuple[str, str, int]:
    """Вернёт (url, name, size). Точное имя → SiPak*.exe → любой .exe → первый файл."""
    want = _asset_name().lower()
    if not assets:
        return "", "", 0

    def url_of(a):
        return (
            a.get("browser_download_url") or "",
            (a.get("name") or "").strip(),
            int(a.get("size") or 0),
        )

    for a in assets:
        name = (a.get("name") or "").strip()
        if name.lower() == want:
            return url_of(a)

    for a in assets:
        low = (a.get("name") or "").lower()
        if "sipak" in low and low.endswith(".exe"):
            return url_of(a)

    for a in assets:
        low = (a.get("name") or "").lower()
        if "sipak" in low:
            return url_of(a)

    for a in assets:
        if (a.get("name") or "").lower().endswith(".exe"):
            return url_of(a)

    return url_of(assets[0])


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


def get_configured_repo() -> str:
    """Репозиторий: вшитый в exe → файл рядом с exe → .env (опционально)."""
    candidates = []

    # 1) вшитый в constants / config
    try:
        from constants import BUILTIN_UPDATE_REPO, UPDATE_GITHUB_REPO

        candidates.append(BUILTIN_UPDATE_REPO)
        candidates.append(UPDATE_GITHUB_REPO)
    except Exception:
        candidates.append(UPDATE_GITHUB_REPO)
    try:
        import config

        candidates.append(getattr(config, "UPDATE_GITHUB_REPO", ""))
        candidates.append(getattr(config, "BUILTIN_UPDATE_REPO", ""))
    except Exception:
        pass

    # 2) файл рядом с exe / программой: update_repo.txt (одна строка user/repo)
    paths = []
    if getattr(sys, "frozen", False):
        paths.append(os.path.join(os.path.dirname(sys.executable), "update_repo.txt"))
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        paths.append(os.path.join(here, "update_repo.txt"))
        paths.append(os.path.join(os.path.dirname(here), "update_repo.txt"))
    except Exception:
        pass
    paths.append(os.path.join(os.getcwd(), "update_repo.txt"))
    for p in paths:
        try:
            if os.path.isfile(p):
                with open(p, "r", encoding="utf-8") as f:
                    line = f.read().strip().splitlines()[0].strip()
                if line and not line.startswith("#"):
                    candidates.insert(0, line)  # файл — приоритетнее пустого builtin
                    break
        except Exception:
            pass

    # 3) .env только если явно задан (не обязателен)
    try:
        from env_load import get as env_get
        from env_load import load_env

        load_env()
        env_repo = (env_get("UPDATE_GITHUB_REPO") or "").strip()
        if env_repo:
            candidates.insert(0, env_repo)
    except Exception:
        pass

    for c in candidates:
        repo = normalize_repo(c or "")
        if repo:
            return repo
    return ""


def check_github_release(repo: str = "") -> dict:
    """
    Проверка latest release.
    Возвращает dict: up_to_date / error / version / download_url / ...
    """
    repo = normalize_repo(repo) or get_configured_repo()
    if not repo or "/" not in repo:
        return {
            "error": "no_repo",
            "up_to_date": True,
            "message": "Обновления не подключены (репозиторий не задан при сборке).",
        }

    url = "https://api.github.com/repos/%s/releases/latest" % repo
    try:
        data = _http_json(url)
    except Exception as e:
        err = str(e)
        # иногда latest нет, но есть список релизов
        if "404" in err:
            try:
                lst = _http_json(
                    "https://api.github.com/repos/%s/releases?per_page=5" % repo
                )
                if isinstance(lst, list) and lst:
                    data = lst[0]
                else:
                    return {
                        "error": "no_releases",
                        "up_to_date": True,
                        "message": (
                            "Репозиторий «%s» найден, но релизов нет.\n"
                            "GitHub → Releases → Create a new release\n"
                            "и прикрепите файл SiPak.exe"
                        )
                        % repo,
                    }
            except Exception as e2:
                return {
                    "error": str(e2),
                    "up_to_date": True,
                    "message": str(e2),
                }
        else:
            return {"error": err, "up_to_date": True, "message": err}

    if not isinstance(data, dict):
        return {
            "error": "bad_response",
            "up_to_date": True,
            "message": "Некорректный ответ GitHub",
        }

    tag = (data.get("tag_name") or data.get("name") or "").strip()
    ver = tag.lstrip("vV")
    if not ver:
        return {
            "error": "no_tag",
            "up_to_date": True,
            "message": "У релиза нет номера версии (tag). Укажите tag вроде v1.0.1",
        }

    html_url = data.get("html_url") or ("https://github.com/%s/releases" % repo)
    notes = (data.get("body") or "")[:1200]
    assets = data.get("assets") or []

    if not is_newer(ver, __version__):
        return {
            "up_to_date": True,
            "version": ver,
            "tag": tag,
            "html_url": html_url,
            "message": "У вас актуальная версия (%s)." % ver,
        }

    download_url, asset_name, asset_size = _pick_asset(assets)
    if not download_url:
        names = ", ".join((a.get("name") or "?") for a in assets[:8]) or "(пусто)"
        return {
            "error": "no_exe_asset",
            "up_to_date": False,
            "version": ver,
            "tag": tag,
            "html_url": html_url,
            "notes": notes,
            "message": (
                "Версия %s есть, но нет файла для скачивания.\n"
                "В релизе прикрепите asset, например SiPak.exe\n"
                "Сейчас в релизе: %s"
            )
            % (ver, names),
        }

    return {
        "up_to_date": False,
        "version": ver,
        "tag": tag,
        "html_url": html_url,
        "notes": notes,
        "download_url": download_url,
        "asset_name": asset_name,
        "asset_size": asset_size,
        "message": "Доступна версия %s (сейчас %s), файл %s"
        % (ver, __version__, asset_name),
    }


def _download(url: str, dest: str, timeout: int = 120) -> None:
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as out:
        while True:
            chunk = resp.read(256 * 1024)
            if not chunk:
                break
            out.write(chunk)


def install_exe_update(download_url: str) -> Tuple[bool, str]:
    """
    Скачать exe и подменить текущий (для frozen / рядом лежащий exe).
    Безопасно: .new → bat/скрипт замены после выхода.
    """
    if not download_url:
        return False, "Нет ссылки для скачивания"

    # куда ставим
    if getattr(sys, "frozen", False):
        target = sys.executable
    else:
        # dev: кладём SiPak.exe рядом с проектом
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        target = os.path.join(root, _asset_name())

    target = os.path.abspath(target)
    folder = os.path.dirname(target)
    base = os.path.basename(target)
    new_path = target + ".new"
    bak_path = target + ".bak"

    try:
        _download(download_url, new_path)
    except Exception as e:
        return False, "Не удалось скачать:\n%s" % e

    if not os.path.isfile(new_path) or os.path.getsize(new_path) < 1000:
        try:
            os.remove(new_path)
        except Exception:
            pass
        return False, "Скачанный файл слишком маленький или повреждён"

    # Windows: helper bat после закрытия
    if sys.platform == "win32":
        bat = os.path.join(folder, "_sipak_update.bat")
        # ждём пока процесс отпустит exe, меняем, запускаем снова
        script = r"""@echo off
setlocal
set TARGET={target}
set NEW={new}
set BAK={bak}
echo Updating SiPak...
:wait
ping -n 2 127.0.0.1 >nul
del "%BAK%" >nul 2>&1
move /Y "%TARGET%" "%BAK%" >nul 2>&1
if exist "%TARGET%" goto wait
move /Y "%NEW%" "%TARGET%" >nul 2>&1
if not exist "%TARGET%" (
  move /Y "%BAK%" "%TARGET%" >nul 2>&1
  echo Restore failed
  pause
  exit /b 1
)
start "" "%TARGET%"
del "%~f0" >nul 2>&1
""".format(target=target, new=new_path, bak=bak_path)
        try:
            with open(bat, "w", encoding="utf-8") as f:
                f.write(script)
            subprocess.Popen(
                ["cmd", "/c", bat],
                cwd=folder,
                close_fds=True,
                creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
            )
            clear_skipped_if_installed("")
            return True, (
                "Обновление подготовлено.\n"
                "Закройте программу — файлы заменятся и СиПак запустится снова.\n"
                "Цель: %s" % target
            )
        except Exception as e:
            return False, "Не удалось запустить установщик:\n%s" % e

    # Linux / mac: replace if writable
    try:
        if os.path.isfile(target):
            try:
                os.replace(target, bak_path)
            except Exception:
                pass
        os.replace(new_path, target)
        try:
            os.chmod(target, 0o755)
        except Exception:
            pass
        return True, "Файл обновлён:\n%s\nПерезапустите программу." % target
    except Exception as e:
        return False, "Не удалось заменить файл:\n%s" % e


def install_zip_source(url: str, project_dir: str) -> Tuple[bool, str]:
    return False, "Установка из zip исходников отключена. Используйте Release с .exe"


def check_git_update(project_dir: str) -> Optional[dict]:
    if not project_dir or not os.path.isdir(os.path.join(project_dir, ".git")):
        return {"error": "no_git", "up_to_date": True}
    try:

        def run(args):
            r = subprocess.run(
                args,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return (r.stdout or "").strip(), r.returncode

        run(["git", "fetch", "origin"])
        local, _ = run(["git", "rev-parse", "--short", "HEAD"])
        remote, code = run(["git", "rev-parse", "--short", "origin/HEAD"])
        if code != 0:
            remote, code = run(["git", "rev-parse", "--short", "origin/main"])
        if code != 0:
            remote, code = run(["git", "rev-parse", "--short", "origin/master"])
        if not remote:
            return {"error": "no_remote", "up_to_date": True}
        if local == remote:
            return {"up_to_date": True, "local": local, "remote": remote}
        return {"up_to_date": False, "local": local, "remote": remote}
    except Exception as e:
        return {"error": str(e), "up_to_date": True}
