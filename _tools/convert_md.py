"""받아 둔 3GPP 본문(docx)을 Markdown 으로 바꾼다.

사용: python convert_md.py [규격번호 ...] [--force] [--no-png]
본문 옆에 <본문 이름>.md 와 media/ 를 만든다. 본문이 .doc(구형 바이너리)이면
표준 라이브러리로 읽을 수 없어, LibreOffice(soffice) 나 Word(Windows) 가 있을 때만
임시 docx 로 바꿔 변환한다. 둘 다 없으면 원문 그대로 둔다.

그림 중 EMF · WMF 는 Markdown 뷰어가 못 그리므로 PNG 를 함께 만들어 md 가 PNG 를
가리키게 한다. Windows 는 GDI+(PowerShell System.Drawing)로, 그 밖에는 Inkscape 가
있으면 그것으로 그린다. 둘 다 없거나 그리기에 실패한 그림은 원래 파일을 가리킨다.
그린 PNG 는 Pillow 로 32색 팔레트로 줄인다 - 3GPP 그림은 선 그림이라 눈으로 차이가 없고
크기가 약 40% 가 된다. Pillow 가 없으면 pip 로 설치한 뒤 쓴다.
--no-png 를 주면 이 단계를 건너뛴다.

3GPP 문서는 스타일이 정형화돼 있어 스타일 이름만으로 구조를 구분한다.
  Heading 1~9 / H6   제목 (Heading 8 · 9 는 Annex 제목이라 1단계로 올린다)
  B1~B5              글머리 (표지 문자 "-" · "a)" 가 본문에 들어 있다)
  PL                 코드 · ASN.1 · XML
  NO · Editor's Note 인용 블록
  TH · TF            표 · 그림 제목
  TOC1~9             목차 (버린다 - 쪽 번호만 남는다)
"""
import base64
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from common import load_release, load_specs, main_doc, spec_dir, stem_of, cover, zip_url

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
V = "urn:schemas-microsoft-com:vml"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def w(tag):
    return f"{{{W}}}{tag}"


# Symbol · Wingdings 글꼴의 기호는 사용자 정의 영역(U+F0xx) 코드로 들어 있어 그대로 두면
# 다른 글꼴에서 깨진다. 글꼴별로 자주 나오는 것만 옮기고, 모르는 코드는 원래 값을 둔다.
SYMBOL = {0xAE: "→", 0xAC: "←", 0xAD: "↑", 0xAF: "↓", 0xDE: "⇒", 0xDC: "⇐",
          0xDB: "⇔", 0xB3: "≥", 0xA3: "≤", 0xB9: "≠", 0xB4: "×", 0xB1: "±",
          0xB7: "•", 0xA5: "∞", 0xD6: "√", 0xE5: "∑", 0xB6: "∂", 0xBB: "≈",
          0x6D: "μ", 0x70: "π", 0x61: "α", 0x62: "β", 0x67: "γ", 0x64: "δ",
          0x44: "Δ", 0x6C: "λ", 0x73: "σ", 0x57: "Ω", 0xC5: "⊕", 0xC4: "⊗",
          0xE0: "◊", 0xB0: "°", 0xCE: "∈", 0xCF: "∉", 0xC7: "∩", 0xC8: "∪",
          0xCC: "⊂", 0xD9: "∧", 0xDA: "∨", 0xD8: "¬", 0xA2: "′", 0xB2: "″", 0xBC: "…"}
# Symbol 글꼴의 영문자 자리는 그리스 문자다 (A -> Α, q -> θ ...)
SYMBOL.update(zip(map(ord, "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"),
                  "ΑΒΧΔΕΦΓΗΙϑΚΛΜΝΟΠΘΡΣΤΥςΩΞΨΖαβχδεφγηιϕκλμνοπθρστυϖωξψζ"))
WINGDINGS = {0xE0: "→", 0xDF: "←", 0xE8: "→", 0xE7: "←", 0xD8: "➢", 0xFC: "✓",
             0xFB: "✗", 0x9F: "•", 0xA7: "▪", 0x6C: "●", 0x6E: "■", 0xF0: "⇒",
             0xF3: "⇔"}


def font_char(font, code):
    """글꼴 이름과 PUA 코드로 실제 문자를 고른다."""
    low = code & 0xFF
    if "wingdings" in (font or "").lower():
        return WINGDINGS.get(low, chr(code))
    if low in SYMBOL:
        return SYMBOL[low]
    # Symbol 글꼴의 숫자 · 문장부호는 ASCII 와 같은 자리에 있다 (영문자 자리는 그리스 문자)
    if 0x20 <= low < 0x7F and not chr(low).isalpha():
        return chr(low)
    return chr(code)

HEADING = re.compile(r"heading (\d)")
BULLET = re.compile(r"b(\d)\+?")
MARKER = re.compile(r"^(-|–|•|\*)\s+")
PUA = re.compile("[\uf000-\uf0ff]")


def kids(el, tag):
    """el 의 직계 tag 자식. sdt · customXml 감싸개는 건너 들어가되 중첩 표 안으로는 들어가지 않는다."""
    for c in el:
        if c.tag == w(tag):
            yield c
        elif c.tag in (w("sdt"), w("sdtContent"), w("customXml")):
            yield from kids(c, tag)


def on(rpr, tag):
    if rpr is None:
        return False
    el = rpr.find(w(tag))
    return el is not None and el.get(w("val"), "true") not in ("0", "false", "none")


class Converter:
    def __init__(self, z, out_dir, media_prefix=""):
        self.z = z
        self.out_dir = out_dir
        self.media_prefix = media_prefix   # 파트 문서끼리 그림 이름(image1.emf)이 겹치지 않게 붙인다
        self.media = {}
        self.metafiles = []     # (원본 이름, PNG 이름) - EMF · WMF 만
        self.names = {posixpath.basename(n) for n in z.namelist()
                      if n.startswith("word/media/")}
        self.fields = []        # 열린 필드마다 "code" / "result"
        self.styles = self._styles()
        self.rels = self._rels()

    # ---- 패키지 메타 ----------------------------------------------------
    def _styles(self):
        try:
            root = ET.fromstring(self.z.read("word/styles.xml"))
        except KeyError:
            return {}
        out = {}
        for st in root.iter(w("style")):
            name = st.find(w("name"))
            out[st.get(w("styleId"))] = (name.get(w("val")) if name is not None
                                         else st.get(w("styleId"))).lower()
        return out

    def _rels(self):
        try:
            root = ET.fromstring(self.z.read("word/_rels/document.xml.rels"))
        except KeyError:
            return {}
        return {r.get("Id"): r.get("Target") for r in root.iter(f"{{{PKG}}}Relationship")
                if r.get("TargetMode") != "External"}

    def image(self, rid):
        target = self.rels.get(rid)
        if not target:
            return ""
        if target not in self.media:
            src = posixpath.normpath(posixpath.join("word", target))
            name = self.media_prefix + posixpath.basename(src)
            try:
                data = self.z.read(src)
            except KeyError:
                return ""
            d = self.out_dir / "media"
            d.mkdir(exist_ok=True)
            (d / name).write_bytes(data)
            link = name
            stem, ext = posixpath.splitext(name)
            if ext.lower() in METAFILE_EXT:
                # 같은 번호의 PNG 가 이미 들어 있으면 image5.emf.png 처럼 원래 확장자를 남긴다
                png = stem + ".png" if stem + ".png" not in self.names else name + ".png"
                self.metafiles.append((name, png))
                link = png
            self.media[target] = link
        return f"![](media/{self.media[target]})"

    # ---- 인라인 ---------------------------------------------------------
    def visible(self):
        return all(f == "result" for f in self.fields)

    def run(self, r, out):
        rpr = r.find(w("rPr"))
        hidden = on(rpr, "vanish")
        fmt = on(rpr, "b")      # 기울임은 버린다 - 굵게와 겹치면 ** · * 표시가 엉킨다
        fonts = rpr.find(w("rFonts")) if rpr is not None else None
        font = None if fonts is None else (fonts.get(w("ascii")) or fonts.get(w("hAnsi")))
        for c in r:
            tag = c.tag
            if tag == w("fldChar"):
                t = c.get(w("fldCharType"))
                if t == "begin":
                    self.fields.append("code")
                elif t == "separate" and self.fields:
                    self.fields[-1] = "result"
                elif t == "end" and self.fields:
                    self.fields.pop()
                continue
            if hidden or not self.visible():
                continue
            if tag == w("t"):
                text = c.text or ""
                if PUA.search(text):
                    text = PUA.sub(lambda m: font_char(font, ord(m.group(0))), text)
                out.append((text, fmt))
            elif tag == w("tab"):
                out.append(("\t", fmt))
            elif tag in (w("br"), w("cr")):
                if c.get(w("type")) != "page":
                    out.append(("\n", fmt))
            elif tag == w("noBreakHyphen"):
                out.append(("-", fmt))
            elif tag == w("sym"):
                code = int(c.get(w("char"), "3F"), 16)
                if code < 0xF000:
                    code += 0xF000     # w:sym 은 F0 접두 없이 적히기도 한다
                out.append((font_char(c.get(w("font")) or font, code), fmt))
            elif tag in (w("drawing"), w("pict"), w("object")):
                for blip in c.iter(f"{{{A}}}blip"):
                    out.append((self.image(blip.get(f"{{{R}}}embed")), "raw"))
                    break
                else:
                    for im in c.iter(f"{{{V}}}imagedata"):
                        out.append((self.image(im.get(f"{{{R}}}id")), "raw"))
                        break

    def inline(self, el, out):
        for c in el:
            tag = c.tag
            if tag == w("r"):
                self.run(c, out)
            elif tag in (w("pPr"), w("rPr"), w("del"), w("moveFrom")):
                continue
            elif tag in (f"{{{M}}}oMath", f"{{{M}}}oMathPara"):
                if self.visible():
                    out.append(("".join(t.text or "" for t in c.iter(f"{{{M}}}t")), False))
            else:   # hyperlink · ins · smartTag · fldSimple · sdt · customXml
                self.inline(c, out)

    @staticmethod
    def render(segs, fmt_ok=True):
        """(텍스트, 서식) 조각을 이어 붙인다. 같은 서식끼리 먼저 합쳐 ** 가 쪼개지지 않게 한다."""
        merged = []
        for text, fmt in segs:
            if merged and merged[-1][1] == fmt and fmt != "raw":
                merged[-1] = (merged[-1][0] + text, fmt)
            else:
                merged.append((text, fmt))
        out = []
        for text, fmt in merged:
            if fmt == "raw" or not fmt_ok or not text.strip():
                out.append(text)
                continue
            if not fmt:
                out.append(text)
                continue
            core = text.strip()
            lead = text[:len(text) - len(text.lstrip())]
            trail = text[len(text.rstrip()):]
            core = core.replace("*", "\\*")
            out.append(f"{lead}**{core}**{trail}")
        # 공백만 끼고 이어진 굵게 조각은 하나로 합친다: **6.1** **General** -> **6.1 General**
        return re.sub(r"\*\*(\s+)\*\*", r"\1", "".join(out))

    # ---- 블록 -----------------------------------------------------------
    def style(self, p):
        ps = p.find(f"{w('pPr')}/{w('pStyle')}")
        sid = ps.get(w("val")) if ps is not None else "Normal"
        return self.styles.get(sid, sid.lower())

    def para(self, p, blocks, in_cell=False):
        name = self.style(p)
        segs = []
        self.inline(p, segs)
        if name.startswith("toc"):
            return
        if name == "pl":
            text = "".join(t for t, _ in segs).replace("\n", " ")
            blocks.append(("code", text.rstrip()))
            return
        m = HEADING.fullmatch(name)
        level = int(m.group(1)) if m else (6 if name == "h6" else 0)
        if level:
            text = re.sub(r"\s+", " ", "".join(t for t, f in segs if f != "raw")).strip()
            if text:
                blocks.append(("text", "#" * (1 if level >= 8 else min(level, 6)) + " " + text))
            return
        text = self.render(segs, fmt_ok=not name.startswith("z"))
        if name in ("no", "ex", "ew", "nw") or "editor" in name:
            text = re.sub(r"\t+", "\t", re.sub(r"[ \u00a0]+", " ", text))
        else:
            text = re.sub(r"[ \t\u00a0]+", " ", text)
        text = text.strip()
        if not text:
            return
        hard = "<br>" if in_cell else "\\\n"
        text = re.sub(r"[ \t]*\n[ \t]*", hard, text)
        if name in ("th", "tf"):
            text = "**" + text.replace("**", "") + "**"
        elif name == "no" or "editor" in name:
            text = "> " + text.replace("\\\n", "\\\n> ")
        else:
            b = BULLET.fullmatch(name)
            if b:
                mk = MARKER.match(text)
                if mk:
                    text = "  " * (int(b.group(1)) - 1) + "- " + text[mk.end():]
        blocks.append(("text", text))

    def cell_text(self, tc):
        sub = []
        for c in tc:
            if c.tag == w("p"):
                self.para(c, sub, in_cell=True)
            elif c.tag == w("tbl"):
                for row in self.rows(c):
                    sub.append(("text", " ".join(x for x in row if x)))
            elif c.tag == w("sdt"):
                for p in c.iter(w("p")):
                    self.para(p, sub, in_cell=True)
        parts = [t.replace("\t", " ") for _, t in sub if t]
        return "<br>".join(parts).replace("|", "\\|")

    def rows(self, tbl):
        out = []
        for tr in kids(tbl, "tr"):
            row = []
            for tc in kids(tr, "tc"):
                pr = tc.find(w("tcPr"))
                span, cont = 1, False
                if pr is not None:
                    gs = pr.find(w("gridSpan"))
                    if gs is not None:
                        span = int(gs.get(w("val"), "1"))
                    vm = pr.find(w("vMerge"))
                    cont = vm is not None and vm.get(w("val"), "continue") == "continue"
                row.append("" if cont else self.cell_text(tc))
                row.extend([""] * (span - 1))
            out.append(row)
        return out

    def table(self, tbl, blocks):
        rows = self.rows(tbl)
        ncol = max((len(r) for r in rows), default=0)
        if ncol <= 1:
            # 한 칸짜리 표는 코드 · 그림 상자로 쓰인다 - 표로 만들지 않고 내용을 블록으로 푼다
            for tr in kids(tbl, "tr"):
                for tc in kids(tr, "tc"):
                    self.blocks(tc, blocks)
            return
        rows = [r + [""] * (ncol - len(r)) for r in rows]
        lines = ["| " + " | ".join(rows[0]) + " |",
                 "|" + " --- |" * ncol]
        lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        blocks.append(("text", "\n".join(lines)))

    def blocks(self, parent, blocks):
        for c in parent:
            if c.tag == w("p"):
                self.para(c, blocks)
            elif c.tag == w("tbl"):
                self.table(c, blocks)
            elif c.tag in (w("sdt"), w("sdtContent"), w("customXml")):
                self.blocks(c, blocks)

    def convert(self):
        body = ET.fromstring(self.z.read("word/document.xml")).find(w("body"))
        blocks = []
        self.blocks(body, blocks)
        out, code = [], []
        for kind, text in blocks + [("end", "")]:
            if kind == "code":
                code.append(text)
                continue
            if code:
                while code and not code[-1].strip():
                    code.pop()
                if code:
                    out.append("```\n" + "\n".join(code) + "\n```")
                code = []
            if kind == "text":
                out.append(text)
        return "\n\n".join(out) + "\n"


# ---- EMF · WMF -> PNG (선택 단계) ------------------------------------------
# 그리는 쪽도 외부 프로그램이라 있을 때만 쓴다. Windows 는 GDI+ 가 늘 있으므로
# PowerShell 의 System.Drawing 으로 그리고, 그 밖에는 Inkscape 를 찾는다.

METAFILE_EXT = (".emf", ".wmf")
FIG_DPI = 200       # 그림 해상도. 3GPP 그림은 대개 A4 본문 폭 이하라 200 이면 글자가 읽힌다
FIG_MAX_PX = 4000   # 한 변 상한 - 쪽 전체 크기로 잘못 잡힌 메타파일이 거대한 PNG 가 되지 않게
FIG_COLORS = 32     # 팔레트 색 수. 선 그림 · 회색 음영 · 강조 몇 색이 들어가는 크기
INKSCAPE_PATHS = [r"C:\Program Files\Inkscape\bin\inkscape.exe",
                  "/Applications/Inkscape.app/Contents/MacOS/inkscape"]

# 목록 파일 한 줄이 "원본<TAB>PNG" 다. 경로는 환경변수와 UTF-8 파일로 넘긴다.
# 메타파일 머리의 경계(Bounds)를 그 해상도(Dpi)로 나누면 인치가 나와 EMF · WMF 모두 같은 식이다.
GDIPLUS_PS = r"""
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$dpi=[double]$env:FIG_DPI; $max=[double]$env:FIG_MAX_PX; $i=0
foreach($line in [IO.File]::ReadAllLines($env:FIG_LIST,[Text.Encoding]::UTF8)){
  $src,$dst=$line -split "`t",2
  try{
    $mf=New-Object System.Drawing.Imaging.Metafile($src)
    try{
      $h=$mf.GetMetafileHeader()
      $w=$h.Bounds.Width/$h.DpiX*$dpi; $ht=$h.Bounds.Height/$h.DpiY*$dpi
      $k=[Math]::Min(1.0,$max/[Math]::Max($w,$ht))
      $w=[Math]::Max(1,[int][Math]::Ceiling($w*$k)); $ht=[Math]::Max(1,[int][Math]::Ceiling($ht*$k))
      $bmp=New-Object System.Drawing.Bitmap($w,$ht)
      try{
        $bmp.SetResolution($dpi,$dpi)
        $g=[System.Drawing.Graphics]::FromImage($bmp)
        try{
          $g.Clear([System.Drawing.Color]::White)
          $g.SmoothingMode='AntiAlias'; $g.InterpolationMode='HighQualityBicubic'
          $g.TextRenderingHint='AntiAliasGridFit'
          $g.DrawImage($mf,0,0,$w,$ht)
        }finally{$g.Dispose()}
        $bmp.Save($dst,[System.Drawing.Imaging.ImageFormat]::Png)
      }finally{$bmp.Dispose()}
    }finally{$mf.Dispose()}
  }catch{ [Console]::Out.WriteLine("FAIL`t$i`t$($_.Exception.Message)") }
  $i++
}
"""


def find_inkscape():
    found = shutil.which("inkscape") or shutil.which("inkscape.exe")
    return found or next((p for p in INKSCAPE_PATHS if Path(p).is_file()), None)


def metafile_renderer():
    """(이름, 함수) 또는 None. 함수는 [(원본, PNG)] -> {실패한 번호: 사유}."""
    if os.name == "nt" and shutil.which("powershell"):
        def run(pairs):
            with tempfile.TemporaryDirectory() as tmp:
                lst = Path(tmp) / "list.txt"
                lst.write_text("\n".join(f"{s.resolve()}\t{d.resolve()}" for s, d in pairs),
                               encoding="utf-8")
                env = dict(os.environ, FIG_LIST=str(lst), FIG_DPI=str(FIG_DPI),
                           FIG_MAX_PX=str(FIG_MAX_PX))
                # 여러 줄 · 따옴표가 든 스크립트라 명령줄 인용에 기대지 않고 -EncodedCommand 로 넘긴다
                enc = base64.b64encode(GDIPLUS_PS.encode("utf-16-le")).decode("ascii")
                r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                                    "-EncodedCommand", enc], env=env, capture_output=True,
                                   timeout=CONVERT_TIMEOUT, check=False)
            out = r.stdout.decode("oem", "replace")
            fails = {}
            for ln in out.splitlines():
                parts = ln.split("\t", 2)
                if len(parts) == 3 and parts[0] == "FAIL" and parts[1].isdigit():
                    fails[int(parts[1])] = parts[2].strip()
            if r.returncode != 0 and not fails:
                err = r.stderr.decode("oem", "replace").strip().splitlines()
                raise RuntimeError(f"GDI+ 실패 (종료 코드 {r.returncode}): {err[0] if err else ''}")
            return fails
        return "GDI+", run
    ink = find_inkscape()
    if ink:
        def run(pairs):
            # Inkscape 는 여러 파일을 한 번에 받으면 원본 옆에 같은 이름의 PNG 를 쓴다.
            # 이미 있는 PNG 를 덮지 않도록 번호 이름으로 임시 폴더에 복사해 그린다.
            with tempfile.TemporaryDirectory() as tmp:
                srcs = []
                for i, (s, _) in enumerate(pairs):
                    c = Path(tmp) / f"{i}{s.suffix.lower()}"
                    shutil.copyfile(s, c)
                    srcs.append(c)
                for k in range(0, len(srcs), 100):   # 명령줄 길이 제한
                    run_tool("Inkscape", [ink, "--export-type=png", "--export-area-drawing",
                                          f"--export-dpi={FIG_DPI}", "--export-background=white",
                                          "--export-background-opacity=1",
                                          *map(str, srcs[k:k + 100])])
                fails = {}
                for i, (c, (_, d)) in enumerate(zip(srcs, pairs)):
                    png = c.with_suffix(".png")
                    if png.is_file():
                        shutil.move(str(png), str(d))
                    else:
                        fails[i] = "PNG 를 만들지 않았다"
                return fails
        return "Inkscape", run
    return None


def require_pillow():
    """Pillow 의 Image 모듈. 없으면 pip 로 설치한 뒤 들여온다."""
    try:
        from PIL import Image
    except ImportError:
        print("Pillow 가 없어 설치한다: pip install pillow", flush=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "pillow"], check=True)
        from PIL import Image
    return Image


def shrink_png(image_mod, png):
    """그린 PNG 를 FIG_COLORS 색 팔레트로 줄여 같은 이름에 다시 쓴다."""
    with image_mod.open(png) as im:
        q = im.convert("RGB").quantize(colors=FIG_COLORS, method=image_mod.Quantize.MEDIANCUT)
    q.save(png, optimize=True)


def render_metafiles(conv, out_dir, renderer):
    """EMF · WMF 를 PNG 로 그린다. (그린 수, 실패 [(원본, PNG, 사유)])."""
    if not conv.metafiles:
        return 0, []
    if renderer is None:
        return 0, [(n, p, "변환기 없음") for n, p in conv.metafiles]
    d = out_dir / "media"
    pairs = [(d / n, d / p) for n, p in conv.metafiles]
    for _, dst in pairs:
        dst.unlink(missing_ok=True)     # 지난번 PNG 가 남아 성공으로 오인되지 않게
    try:
        fails = renderer[1](pairs)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        return 0, [(n, p, str(exc)[:200]) for n, p in conv.metafiles]
    bad = []
    image_mod = require_pillow()
    for i, ((n, p), (_, dst)) in enumerate(zip(conv.metafiles, pairs)):
        if i in fails or not dst.is_file():
            bad.append((n, p, fails.get(i, "PNG 없음")))
        else:
            shrink_png(image_mod, dst)
    return len(pairs) - len(bad), bad


def yaml_str(s):
    return '"' + (s or "").replace("\\", "\\\\").replace('"', '\\"') + '"'


# ---- .doc -> docx (선택 단계) ---------------------------------------------
# 변환기는 외부 프로그램이라 있을 때만 쓴다. LibreOffice 를 먼저 찾고, 없으면
# Windows 의 Word 를 PowerShell COM 으로 부른다 (pywin32 를 쓰지 않으려고).

SOFFICE_PATHS = [r"C:\Program Files\LibreOffice\program\soffice.exe",
                 "/Applications/LibreOffice.app/Contents/MacOS/soffice"]

# 경로는 환경변수로 넘긴다 - 명령 문자열에 끼우면 따옴표 · 대괄호 경로가 깨진다
WORD_PS = (
    "$ErrorActionPreference='Stop';"
    "$w=New-Object -ComObject Word.Application;$w.Visible=$false;$w.DisplayAlerts=0;"
    "try{$d=$w.Documents.Open($env:SRC_DOC,$false,$true,$false);"
    "$d.SaveAs2($env:DST_DOCX,16);$d.Close($false)}finally{$w.Quit()}"
)
# COM 으로 뜬 Word 는 명령줄에 /Automation 이 붙는다 - 사용자가 연 Word 와 구분하는 표지
WORD_PIDS_PS = ("Get-CimInstance Win32_Process -Filter \"Name='WINWORD.EXE'\" | "
                "Where-Object CommandLine -match '/Automation' | ForEach-Object ProcessId")
CONVERT_TIMEOUT = 600  # 초. 24.229(.doc 16 MB) 도 Word 로 수십 초면 끝난다


def run_tool(name, cmd, **kw):
    """변환기를 돌리고, 실패하면 stderr 첫 줄을 담은 RuntimeError 로 바꾼다."""
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=CONVERT_TIMEOUT, **kw)
    except subprocess.CalledProcessError as exc:
        # Windows 콘솔 도구는 파이프에 OEM 코드 페이지로 쓴다
        err = exc.stderr.decode("oem" if os.name == "nt" else "utf-8", "replace")
        first = next((ln.strip() for ln in err.splitlines() if ln.strip()), "")
        raise RuntimeError(f"{name} 실패 (종료 코드 {exc.returncode}): {first}") from None
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{name} 가 {CONVERT_TIMEOUT}초 안에 끝나지 않았다") from None


def word_pids():
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", WORD_PIDS_PS],
                       capture_output=True, text=True, check=False)
    return {int(x) for x in r.stdout.split() if x.isdigit()}


def find_soffice():
    found = shutil.which("soffice") or shutil.which("soffice.exe")
    return found or next((p for p in SOFFICE_PATHS if Path(p).is_file()), None)


def has_word():
    if os.name != "nt":
        return False
    import winreg
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"))
        return True
    except OSError:
        return False


def doc_converter():
    """(이름, 함수) 또는 None. 함수는 (doc 경로, 출력 폴더) -> 만든 docx 경로."""
    so = find_soffice()
    if so:
        def run(doc, out):
            # 별도 프로필을 주지 않으면 이미 떠 있는 LibreOffice 에 일을 넘기고
            # 아무것도 만들지 않은 채 0 으로 끝난다
            profile = (out / "lo-profile").as_uri()
            run_tool("LibreOffice", [so, f"-env:UserInstallation={profile}", "--headless",
                                     "--convert-to", "docx", "--outdir", str(out), str(doc)])
            return out / f"{doc.stem}.docx"
        return "LibreOffice", run
    if has_word():
        def run(doc, out):
            dst = out / f"{doc.stem}.docx"
            env = dict(os.environ, SRC_DOC=str(doc.resolve()), DST_DOCX=str(dst))
            before = word_pids()
            try:
                run_tool("Word", ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                                  WORD_PS], env=env)
            except RuntimeError:
                # powershell 이 죽어도 COM 이 띄운 Word 는 자식이 아니라 숨은 채 남는다.
                # 대화상자에 막힌 Word 가 파일을 잡고 쌓이지 않도록 이번에 뜬 것만 끈다.
                for pid in word_pids() - before:
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                                   capture_output=True, check=False)
                raise
            return dst
        return "Word", run
    return None


def convert_one(e, force, doc_conv, fig_conv=None):
    d = spec_dir(e)
    doc, code = main_doc(d, e["spec"], e, load_release())
    if doc is None:
        return "MISSING", "본문 없음 (fetch 먼저)"
    is_doc = doc.suffix.lower() == ".doc"
    if is_doc and doc_conv is None:
        return "DOC", f"{doc.name} (LibreOffice · Word 없음)"
    md = d / f"{doc.stem}.md"
    _, url = zip_url(e["spec"], code)
    if md.exists() and not force and md.stat().st_mtime >= doc.stat().st_mtime:
        if e.get("parts"):
            return "SKIP", md.name + " / " + convert_parts(e, d, doc, code, url, cover(doc), force, doc_conv, fig_conv)
        return "SKIP", md.name
    # Word 가 종료 직후 잠시 파일을 잡고 있어 임시 폴더 정리 실패는 무시한다
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        src = doc_conv[1](doc, Path(tmp)) if is_doc else doc
        if not src.is_file():
            raise RuntimeError(f"{doc_conv[0]} 가 docx 를 만들지 않았다")
        # .doc 표지는 ASCII 구간만 긁어 손실이 있으므로 변환한 docx 에서 읽는다
        c = cover(src)
        with zipfile.ZipFile(src) as z:
            conv = Converter(z, d)
            body = conv.convert()
    if fig_conv is False:   # --no-png
        n_png, bad = 0, [(n, p, "건너뜀") for n, p in conv.metafiles]
    else:
        n_png, bad = render_metafiles(conv, d, fig_conv)
    # 그리지 못한 그림은 링크를 원래 파일로 되돌린다
    for n, p, _ in bad:
        body = body.replace(f"](media/{p})", f"](media/{n})")
    kind = (c["kind"] or e["kind"]).upper()
    head = ["---",
            f"spec: {yaml_str(kind + ' ' + e['spec'])}",
            f"title: {yaml_str(c['title'])}",
            f"version: {yaml_str(c['ver'])}",
            f"release: {c['release'] if c['release'] is not None else 'null'}",
            f"date: {yaml_str(c['date'])}",
            f"source: {yaml_str(url)}",
            f"converted_from: {yaml_str(doc.name)}",
            "---", ""]
    md.write_text("\n".join(head) + body, encoding="utf-8", newline="\n")
    via = f", {doc_conv[0]} 로 docx 변환" if is_doc else ""
    fig = ""
    if conv.metafiles and fig_conv is not False:
        fig = f", PNG {n_png}/{len(conv.metafiles)}"
        if bad and n_png:
            fig += f" (실패 예: {bad[0][0]} - {bad[0][2][:80]})"
    msg = (f"{md.name} ({md.stat().st_size / 1e6:.1f} MB, 그림 {len(conv.media)}"
           f"{fig}{via})")
    if e.get("parts"):
        msg += " / " + convert_parts(e, d, doc, code, url, c, force, doc_conv, fig_conv)
    return "MD", msg


def part_docs(d, spec, code):
    """장별로 나뉜 파트 문서(<번호>-<판>_<파트>_....doc/.docx). 같은 이름이면 docx 를 고른다."""
    prefix = f"{stem_of(spec)}-{code}_"
    found = {}
    for p in sorted(d.iterdir()):
        if p.is_file() and p.name.lower().startswith(prefix) and p.suffix.lower() in (".doc", ".docx"):
            if p.stem not in found or p.suffix.lower() == ".docx":
                found[p.stem] = p
    return list(found.values())


def convert_parts(e, d, main, code, url, c, force, doc_conv, fig_conv):
    """specs.json 항목의 "parts"(파트 표지 목록, 예 ["a"])에 든 파트 문서마다 <파트 문서 이름>.md 를 만든다.
    코덱 알고리즘 본문처럼 근거로 쓰지 않는 파트는 수식 그림이 수천 개라 목록에서 뺀다 (26.445 는 Annex A 만).

    표지는 본문(main)의 것을 쓴다. 그림은 media/<파트>_<원래 이름> 으로 둔다.
    """
    done, skipped, bad = [], [], []
    for part in part_docs(d, e["spec"], code):
        md = d / f"{part.stem}.md"
        if md.exists() and not force and md.stat().st_mtime >= part.stat().st_mtime:
            skipped.append(md.name)
            continue
        is_doc = part.suffix.lower() == ".doc"
        if is_doc and doc_conv is None:
            bad.append(f"{part.name}(.doc 변환기 없음)")
            continue
        tag = part.stem[len(f"{stem_of(e['spec'])}-{code}_"):].split("_", 1)[0]
        if tag not in e["parts"]:
            continue
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            src = doc_conv[1](part, Path(tmp)) if is_doc else part
            with zipfile.ZipFile(src) as z:
                conv = Converter(z, d, media_prefix=f"{tag}_")
                body = conv.convert()
        if fig_conv is not False:
            _, fails = render_metafiles(conv, d, fig_conv)
            for n, pn, _ in fails:
                body = body.replace(f"](media/{pn})", f"](media/{n})")
        kind = (c["kind"] or e["kind"]).upper()
        head = ["---",
                f"spec: {yaml_str(kind + ' ' + e['spec'])}",
                f"title: {yaml_str(c['title'])}",
                f"version: {yaml_str(c['ver'])}",
                f"release: {c['release'] if c['release'] is not None else 'null'}",
                f"date: {yaml_str(c['date'])}",
                f"part: {yaml_str(part.stem)}",
                f"source: {yaml_str(url)}",
                f"converted_from: {yaml_str(part.name)}",
                "---", ""]
        md.write_text("\n".join(head) + body, encoding="utf-8", newline="\n")
        done.append(md.name)
    out = f"파트 {len(done)}건 변환"
    if skipped:
        out += f", {len(skipped)}건 최신"
    if bad:
        out += f", 실패 {', '.join(bad)}"
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    no_png = "--no-png" in sys.argv
    specs = [e for e in load_specs() if not args or e["spec"] in args]
    doc_conv = doc_converter()
    print(f".doc 변환기: {doc_conv[0] if doc_conv else '없음 (.doc 본문은 건너뜀)'}")
    fig_conv = False if no_png else metafile_renderer()
    if fig_conv:
        require_pillow()    # 변환을 시작하기 전에 한 번 - 도중에 설치로 멈추지 않게
    print("EMF · WMF -> PNG: " + ("건너뜀 (--no-png)" if fig_conv is False else
                                 fig_conv[0] if fig_conv else "변환기 없음 (원본 링크 유지)"))
    res = []
    for e in specs:
        try:
            st, msg = convert_one(e, force, doc_conv, fig_conv)
        except Exception as exc:  # noqa: BLE001
            st, msg = "FAIL", f"{type(exc).__name__}: {str(exc)[:300]}"
        res.append((e["spec"], st, msg))
        print(f"{st:7s} {e['spec']:12s} {msg}", flush=True)
    print("\n===== 요약 =====")
    for st in ("MD", "SKIP", "DOC", "MISSING", "FAIL"):
        n = [r for r in res if r[1] == st]
        if n:
            print(f"{st}: {len(n)}건" + (" - " + ", ".join(r[0] for r in n)
                                        if st in ("DOC", "MISSING", "FAIL") else ""))


if __name__ == "__main__":
    main()
