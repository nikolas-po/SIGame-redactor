# -*- coding: utf-8 -*-

import os
import uuid
import zipfile
import tempfile
import xml.etree.ElementTree as ET

from constants import NS, MEDIA_FOLDERS, MEDIA_EXTS
from models import Package, Round, Theme, Question, Atom

ET.register_namespace("", NS)


def _local(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def _safe_int(value, default=0, min_v=None, max_v=None):
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    if min_v is not None:
        n = max(min_v, n)
    if max_v is not None:
        n = min(max_v, n)
    return n


def package_to_xml(pkg):
    attrs = {
        "name": (pkg.name or "Пакет")[:200],
        "version": "4",
        "id": pkg.package_id or str(uuid.uuid4()),
        "date": pkg.date or "",
        "difficulty": str(_safe_int(pkg.difficulty, 4, 1, 10)),
        "restriction": pkg.restriction or "12+",
        "language": pkg.language or "ru-RU",
    }
    if getattr(pkg, "publisher", ""):
        attrs["publisher"] = str(pkg.publisher)[:200]
    if getattr(pkg, "logo", ""):
        attrs["logo"] = "@" + str(pkg.logo).lstrip("@")

    root = ET.Element("{%s}package" % NS, attrs)

    if pkg.tags:
        tags_el = ET.SubElement(root, "{%s}tags" % NS)
        for t in pkg.tags:
            if t and str(t).strip():
                te = ET.SubElement(tags_el, "{%s}tag" % NS)
                te.text = str(t).strip()[:100]

    info = ET.SubElement(root, "{%s}info" % NS)
    authors = ET.SubElement(info, "{%s}authors" % NS)
    if pkg.author:
        a = ET.SubElement(authors, "{%s}author" % NS)
        a.text = str(pkg.author)[:200]
    if pkg.comments:
        c = ET.SubElement(info, "{%s}comments" % NS)
        c.text = str(pkg.comments)[:5000]

    rounds_el = ET.SubElement(root, "{%s}rounds" % NS)
    for rnd in pkg.rounds:
        r_attrs = {"name": (rnd.name or "Раунд")[:200]}
        if rnd.is_final:
            r_attrs["type"] = "final"
        r_el = ET.SubElement(rounds_el, "{%s}round" % NS, r_attrs)
        themes_el = ET.SubElement(r_el, "{%s}themes" % NS)
        for theme in rnd.themes:
            t_el = ET.SubElement(
                themes_el, "{%s}theme" % NS, {"name": (theme.name or "Тема")[:200]}
            )
            qs_el = ET.SubElement(t_el, "{%s}questions" % NS)
            for q in theme.questions:
                q_el = ET.SubElement(
                    qs_el,
                    "{%s}question" % NS,
                    {"price": str(_safe_int(q.price, 100, 1, 999999))},
                )
                if q.qtype and q.qtype != "simple":
                    type_el = ET.SubElement(q_el, "{%s}type" % NS, {"name": q.qtype})
                    if q.qtype in ("cat", "bagcat"):
                        if q.secret_theme:
                            p = ET.SubElement(type_el, "{%s}param" % NS, {"name": "theme"})
                            p.text = str(q.secret_theme)[:200]
                        if q.secret_cost:
                            p = ET.SubElement(type_el, "{%s}param" % NS, {"name": "cost"})
                            p.text = str(_safe_int(q.secret_cost, 0, 0, 999999))
                        if q.qtype == "bagcat":
                            p = ET.SubElement(type_el, "{%s}param" % NS, {"name": "self"})
                            p.text = "true" if getattr(q, "cat_self", True) else "false"
                            p = ET.SubElement(type_el, "{%s}param" % NS, {"name": "knows"})
                            knows = getattr(q, "cat_knows", "before") or "before"
                            if knows not in ("before", "after", "never"):
                                knows = "before"
                            p.text = knows

                sc = ET.SubElement(q_el, "{%s}scenario" % NS)
                atoms = q.atoms if q.atoms else [Atom("text", "")]
                for atom in atoms:
                    _write_atom(sc, atom)
                if q.answer_atoms:
                    ET.SubElement(sc, "{%s}atom" % NS, {"type": "marker"})
                    for atom in q.answer_atoms:
                        _write_atom(sc, atom)

                right = ET.SubElement(q_el, "{%s}right" % NS)
                answers = list(q.answers or [""]) or [""]
                for ans in answers:
                    ae = ET.SubElement(right, "{%s}answer" % NS)
                    ae.text = str(ans if ans is not None else "")[:500]

                if q.wrong:
                    wrong = ET.SubElement(q_el, "{%s}wrong" % NS)
                    for w in q.wrong:
                        if w:
                            we = ET.SubElement(wrong, "{%s}answer" % NS)
                            we.text = str(w)[:500]

                if q.comment:
                    qinfo = ET.SubElement(q_el, "{%s}info" % NS)
                    qc = ET.SubElement(qinfo, "{%s}comments" % NS)
                    qc.text = str(q.comment)[:2000]

    _indent(root)
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode")


def _write_atom(parent, atom):
    attrs = {"type": atom.atype or "text"}
    if atom.duration:
        attrs["time"] = str(_safe_int(atom.duration, 0, 0, 3600))
    a_el = ET.SubElement(parent, "{%s}atom" % NS, attrs)
    val = atom.value or ""
    if atom.atype in ("image", "voice", "video"):
        if val and not val.startswith("@") and not str(val).startswith("http"):
            val = "@" + val
        a_el.text = val
    else:
        a_el.text = str(val)[:5000]


def _indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i


def parse_siq_xml(xml_bytes, media_extract_dir=None):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise ValueError("Файл повреждён или это не пакет SIGame.\n%s" % e)

    pkg = Package()
    pkg.name = root.get("name") or "Пакет"
    pkg.package_id = root.get("id") or str(uuid.uuid4())
    pkg.date = root.get("date") or ""
    pkg.difficulty = _safe_int(root.get("difficulty"), 4, 1, 10)
    pkg.restriction = root.get("restriction") or "12+"
    pkg.language = root.get("language") or "ru-RU"
    pkg.publisher = root.get("publisher") or ""
    logo = root.get("logo") or ""
    pkg.logo = logo.lstrip("@") if logo else ""

    for child in root:
        tag = _local(child.tag)
        if tag == "tags":
            pkg.tags = [
                t.text.strip()
                for t in child
                if _local(t.tag) == "tag" and t.text and t.text.strip()
            ]
        elif tag == "info":
            for info_child in child:
                itag = _local(info_child.tag)
                if itag == "authors":
                    for a in info_child:
                        if _local(a.tag) == "author" and a.text:
                            pkg.author = a.text
                            break
                elif itag == "comments" and info_child.text:
                    pkg.comments = info_child.text
        elif tag == "rounds":
            for r_el in child:
                if _local(r_el.tag) != "round":
                    continue
                rnd = Round(r_el.get("name") or "Раунд")
                rnd.is_final = (r_el.get("type") or "").lower() == "final"
                for t_container in r_el:
                    if _local(t_container.tag) != "themes":
                        continue
                    for t_el in t_container:
                        if _local(t_el.tag) != "theme":
                            continue
                        theme = Theme(t_el.get("name") or "Тема")
                        for qs_container in t_el:
                            if _local(qs_container.tag) != "questions":
                                continue
                            for q_el in qs_container:
                                if _local(q_el.tag) != "question":
                                    continue
                                theme.questions.append(
                                    _parse_question(q_el, pkg, media_extract_dir)
                                )
                        rnd.themes.append(theme)
                pkg.rounds.append(rnd)
    return pkg


def _parse_question(q_el, pkg, media_extract_dir):
    q = Question()
    q.price = _safe_int(q_el.get("price"), 100, 1, 999999)
    q.atoms = []
    q.answer_atoms = []
    in_answer = False

    for part in q_el:
        ptag = _local(part.tag)
        if ptag == "type":
            q.qtype = part.get("name") or "simple"
            for param in part:
                if _local(param.tag) != "param":
                    continue
                pname = param.get("name")
                ptext = (param.text or "").strip()
                if pname == "theme":
                    q.secret_theme = ptext
                elif pname == "cost":
                    q.secret_cost = _safe_int(ptext, 0, 0, 999999)
                elif pname == "self":
                    q.cat_self = ptext.lower() == "true"
                elif pname == "knows":
                    q.cat_knows = ptext.lower() if ptext else "before"
        elif ptag == "scenario":
            for atom_el in part:
                if _local(atom_el.tag) != "atom":
                    continue
                atype = atom_el.get("type") or "text"
                if atype == "marker":
                    in_answer = True
                    continue
                val = (atom_el.text or "").strip()
                if val.startswith("@"):
                    val = val[1:]
                atom = Atom(atype, val, _safe_int(atom_el.get("time"), 0, 0, 3600))
                if media_extract_dir and atype in MEDIA_FOLDERS and val:
                    folder = MEDIA_FOLDERS[atype]
                    candidate = os.path.join(media_extract_dir, folder, val)
                    if os.path.isfile(candidate):
                        atom.local_path = candidate
                        pkg.media_files[val] = candidate
                if in_answer:
                    q.answer_atoms.append(atom)
                else:
                    q.atoms.append(atom)
            if not q.atoms:
                q.atoms = [Atom("text", "")]
        elif ptag == "right":
            q.answers = []
            for ans in part:
                if _local(ans.tag) == "answer":
                    q.answers.append((ans.text or "").strip())
            if not q.answers:
                q.answers = [""]
        elif ptag == "wrong":
            q.wrong = [
                (ans.text or "").strip()
                for ans in part
                if _local(ans.tag) == "answer" and ans.text
            ]
        elif ptag == "info":
            for ic in part:
                if _local(ic.tag) == "comments" and ic.text:
                    q.comment = ic.text.strip()
    return q


def save_siq(pkg, path):
    if not path:
        raise ValueError("Не указан путь для сохранения.")
    if not str(path).lower().endswith(".siq"):
        path = path + ".siq"

    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        raise ValueError("Папка не существует:\n%s" % parent)

    xml = package_to_xml(pkg)
    content_types = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '  <Default Extension="xml" ContentType="text/xml"/>\n'
        '  <Default Extension="jpg" ContentType="image/jpeg"/>\n'
        '  <Default Extension="jpeg" ContentType="image/jpeg"/>\n'
        '  <Default Extension="png" ContentType="image/png"/>\n'
        '  <Default Extension="gif" ContentType="image/gif"/>\n'
        '  <Default Extension="mp3" ContentType="audio/mpeg"/>\n'
        '  <Default Extension="wav" ContentType="audio/wav"/>\n'
        '  <Default Extension="ogg" ContentType="audio/ogg"/>\n'
        '  <Default Extension="mp4" ContentType="video/mp4"/>\n'
        '  <Default Extension="webm" ContentType="video/webm"/>\n'
        "</Types>\n"
    )

    tmp_path = path + ".tmp"
    try:
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("content.xml", xml.encode("utf-8"))
            zf.writestr("[Content_Types].xml", content_types.encode("utf-8"))
            written = set()
            for fname, local in list(pkg.media_files.items()):
                if not local or not os.path.isfile(local) or fname in written:
                    continue
                safe = os.path.basename(str(fname).replace("\\", "/"))
                if not safe or safe in (".", ".."):
                    continue
                ext = os.path.splitext(safe)[1].lower()
                folder = "Images"
                for atype, exts in MEDIA_EXTS.items():
                    if ext in exts:
                        folder = MEDIA_FOLDERS[atype]
                        break
                try:
                    zf.write(local, "%s/%s" % (folder, safe))
                    written.add(fname)
                except OSError:
                    continue
        os.replace(tmp_path, path)
    except Exception:
        if os.path.isfile(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise
    return path


def load_siq(path):
    if not path or not os.path.isfile(path):
        raise ValueError("Файл не найден:\n%s" % (path or ""))
    size = os.path.getsize(path)
    if size == 0:
        raise ValueError("Файл пустой.")
    if size > 500 * 1024 * 1024:
        raise ValueError("Файл слишком большой (больше 500 МБ).")

    extract_dir = tempfile.mkdtemp(prefix="siq_media_")
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            if "content.xml" not in names:
                raise ValueError("Это не пакет SIGame.\nВнутри нет content.xml.")
            for name in names:
                norm = name.replace("\\", "/")
                if norm.startswith("/") or ".." in norm.split("/"):
                    raise ValueError("Подозрительный файл внутри архива.")
            zf.extractall(extract_dir)
            xml_data = zf.read("content.xml")
    except zipfile.BadZipFile:
        raise ValueError("Файл повреждён или это не .siq.")

    pkg = parse_siq_xml(xml_data, media_extract_dir=extract_dir)
    for folder in ("Images", "Audio", "Video"):
        d = os.path.join(extract_dir, folder)
        if os.path.isdir(d):
            for fn in os.listdir(d):
                full = os.path.join(d, fn)
                if os.path.isfile(full):
                    pkg.media_files[fn] = full
    return pkg


def validate_package(pkg):
    warnings = []
    errors = []

    if not (pkg.name or "").strip():
        errors.append("У пакета нет названия.")

    if not pkg.rounds:
        errors.append("Нет ни одного раунда.")
    else:
        for r in pkg.rounds:
            if not r.themes:
                warnings.append("Раунд «%s» без тем." % (r.name or "?"))

    n_q = 0
    empty_q = 0
    no_answer = 0
    for ri, rnd in enumerate(pkg.rounds):
        for theme in rnd.themes:
            if not theme.questions:
                warnings.append("Тема «%s» без вопросов." % (theme.name or "?"))
            for q in theme.questions:
                n_q += 1
                if not q.has_text_or_media():
                    empty_q += 1
                if not q.has_answer():
                    no_answer += 1
                if q.qtype in ("cat", "bagcat") and not (q.secret_theme or "").strip():
                    warnings.append(
                        "Кот без секретной темы («%s», %d)."
                        % (theme.name, q.price)
                    )

    if n_q == 0:
        errors.append("Нет ни одного вопроса.")
    if empty_q:
        warnings.append("Вопросов без текста и медиа: %d." % empty_q)
    if no_answer:
        warnings.append("Вопросов без правильного ответа: %d." % no_answer)

    return errors, warnings
