#!/usr/bin/env python3
"""Markdownの表記規約とリンクを機械的に扱うPostToolUseフック(ファイル作成かファイル編集した直後に走るフック)兼、一括修正・一括検査のCLI。

直し方が一意に決まるものは自動で修正し、判断を要するものは検出して差し戻す。対象はリポジトリ内のMarkdownのみ。

  §6: 和欧間スペース        → 自動修正
  見出しのアンカー           → 自動修正(和欧間スペースの削除で見出しのアンカーが変わったら、そのアンカーへのリンクを書き換える)
  リンク切れ                 → 検出のみ(リンク先のファイルや見出しが無い)
  §2: HTMLコメント破壊      → 検出のみ
  強調記法の不成立           → 検出のみ
  コードブロックの閉じ忘れ    → 検出のみ
  表の列数の不一致           → 検出のみ
  §1: プレースホルダ残存     → 検出のみ(docs/配下)
  §7: ID形式                → 検出のみ(docs/配下)

スコープの粒度・文体・参照元の境界のような判断を要する規約は扱わない。

  一括修正: python3 -I lint-text-style.py --fix [<path>...]
  一括検査: python3 -I lint-text-style.py --check [<path>...]  ファイルは書き換えず、問題があれば終了コード1を返す
  <path>を省くと、リポジトリ内のMarkdownすべてが対象になる。
"""
import io
import json
import os
import posixpath
import re
import subprocess
import sys
import unicodedata
from urllib.parse import quote, unquote

JP = r'ぁ-んァ-ヶー一-龥々〆'
JP_CHAR = re.compile(r'[' + JP + r']')
ALNUM = re.compile(r'[0-9A-Za-z]')
MAX_REPORT = 8

# 自動修正の対象となる空白(キャプチャ1が削除対象)
SPACE_PATTERNS = [
    re.compile(r'(?<=[' + JP + r'])( +)(?=[0-9A-Za-z`%])'),
    re.compile(r'(?<=[0-9A-Za-z`%])( +)(?=[' + JP + r'])'),
]

# 正規表現の補足
# マークダウンにおいて`**`が太字になるには、内側(太字にする文字列の側)が空白でないことに加えて、
# 内側が記号(「 ( 、 等)なら外側も空白か記号である必要がある
#
#   太字になる    ...を **「なぜやるのか」** と...   内側=「 外側=空白
#   太字になる    ...は**候補者評価**を...           内側=候(記号でない)
#   ならない      ...を**「なぜやるのか」**と...     内側=「 外側=を
#
# そのため、和欧間の半角スペースを詰める際、内側が記号になっている`**`については、
# 外側の空白を残す。消すと太字が効かなくなったり、開始と終了の対応がずれて別の範囲が太字になったりする。
# また、英単語どうしの間の空白(`use **strict** mode`)は和欧間ではないため残す。
BOLD_CLOSE = re.compile(r'\*\*( +)(?=\S)')   # `**`の後ろの空白(閉じ側)
BOLD_OPEN = re.compile(r'( +)\*\*(?=\S)')    # `**`の前の空白(開き側)

ASCII_PUNCT = set('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')


# 見出しの先頭の番号と見出し名の間の空白(`#### 2.1 上流を読む`)は、和欧間の空白の例外として残す
HEADING_NUMBER = re.compile(r'^#{1,6} [0-9]+(?:\.[0-9]+)*\.?( +)')


def base_before(sh, i):
    """位置iの直前の文字を返す。異体字セレクタなどの結合文字は飛ばし、その前の文字を返す。

    `⚠️`は`⚠`の後ろに見えない異体字セレクタが付いた2文字で、セレクタだけを見ると記号と判定できない。
    """
    i -= 1
    while i >= 0 and unicodedata.category(sh[i])[0] == 'M':
        i -= 1
    return sh[i] if i >= 0 else ''


def is_punct(ch):
    """記号か(括弧・句読点を含む)。空文字は行頭・行末を表す。"""
    if not ch:
        return True
    if ch in ASCII_PUNCT:
        return True
    return unicodedata.category(ch)[0] in 'PS'


def is_jp(ch):
    return bool(ch) and JP_CHAR.match(ch) is not None


def is_alnum(ch):
    return bool(ch) and ALNUM.match(ch) is not None


def removable_pair(a, b):
    """空白を挟む2文字が、空白を詰めてよい組か。片方が和文で、もう片方が和文か英数字の場合に限る。

    記号を含む組(太字が効かなくなる)と、英数字どうしの組(英単語の区切り)は詰めない。
    """
    return (is_jp(a) and (is_jp(b) or is_alnum(b))) or (is_alnum(a) and is_jp(b))


def bold_space_spans(sh):
    """強調記法に隣接する削除可能な空白の範囲を返す。"""
    spans = []
    for m in BOLD_CLOSE.finditer(sh):   # 内側=`**`の直前、外側=空白の直後
        inner = base_before(sh, m.start())
        outer = sh[m.end():m.end() + 1]
        if removable_pair(inner, outer):
            spans.append(m.span(1))
    for m in BOLD_OPEN.finditer(sh):    # 外側=空白の直前、内側=`**`の直後
        outer = base_before(sh, m.start())
        inner = sh[m.end():m.end() + 1]
        if removable_pair(outer, inner):
            spans.append(m.span(1))
    return spans

CODE_SPAN = re.compile(r'``.*?``|`[^`]*`')
URL = re.compile(r'(?:https?://|www\.)[^\s<>]*')
PAT_ROW = re.compile(r'^\|\s*([A-Za-z0-9_-]+)\s*\|')
PAT_ID_NOHYPHEN = re.compile(r'^[A-Z]{2,}[0-9]+$')
PAT_ID_LOWER = re.compile(r'^[a-z][a-z0-9]*(-[a-z0-9]+)+$')


def shadow(line):
    """インラインコードの中身とURLを中立文字に置いた同じ長さの文字列を返す。

    インラインコードは前後のバッククォートを残すため、和文とコードの境界は判定できる。
    URLは全体を置き換え、前後の空白を残す。空白を詰めるとURLが自動リンクにならないか、後ろの和文までURLに含まれるため。
    """
    buf = list(line)
    for m in CODE_SPAN.finditer(line):
        s, e = m.span()
        n = 2 if line[s:s + 2] == '``' else 1
        for i in range(s + n, e - n):
            buf[i] = '\x01'
    # インラインコードの中のURLは置き換え済みのため、置き換え後の文字列から探す
    for m in URL.finditer(''.join(buf)):
        for i in range(*m.span()):
            buf[i] = '\x01'
    return ''.join(buf)


def fix_line(line):
    """1行から和欧間スペースを取り除く。コードブロック外の行にのみ適用する。"""
    sh = shadow(line)
    spans = []
    for pat in SPACE_PATTERNS:
        spans.extend(m.span(1) for m in pat.finditer(sh))
    spans.extend(bold_space_spans(sh))
    m = HEADING_NUMBER.match(sh)
    if m:
        spans = [s for s in spans if s != m.span(1)]
    if not spans:
        return line, 0
    for s, e in sorted(set(spans), reverse=True):
        line = line[:s] + line[e:]
    return line, len(set(spans))


# ---------------------------------------------------------------------------
# 行の分類(コードブロック・HTMLコメント・フロントマター)

FENCE_OPEN = re.compile(r'^\s*(`{3,}|~{3,})')


def code_block_flags(lines):
    """各行がフェンスコードブロック(開始行・終了行を含む)に入っているかを返す。

    戻り値は (行ごとの真偽値のリスト, 閉じられていないブロックの開始行番号。無ければ0)。
    """
    flags, fence, start = [], None, 0
    for no, ln in enumerate(lines, 1):
        if fence is None:
            m = FENCE_OPEN.match(ln)
            # バッククォートのフェンスは、情報文字列にバッククォートを含められない(含むならインラインコード)
            if m and not (m.group(1)[0] == '`' and '`' in ln[m.end():]):
                fence, start = m.group(1), no
                flags.append(True)
            else:
                flags.append(False)
            continue
        flags.append(True)
        s = ln.strip()
        if s and set(s) == {fence[0]} and len(s) >= len(fence):
            fence = None
    return flags, (start if fence else 0)


def content_lines(lines):
    """フロントマター・コードブロック・HTMLコメントを除いた本文の行を (行番号, 行) で返す。

    行内のHTMLコメントは同じ長さの空白に置き換えるため、列位置は元の行と一致する。
    """
    flags, _ = code_block_flags(lines)
    front_end = 0
    if lines and lines[0].strip() == '---':
        for i in range(1, len(lines)):
            if lines[i].strip() in ('---', '...'):
                front_end = i + 1
                break
    out, in_comment = [], False
    for no, (ln, code) in enumerate(zip(lines, flags), 1):
        if no <= front_end or code:
            continue
        if in_comment:
            end = ln.find('-->')
            if end < 0:
                continue
            ln = ' ' * (end + 3) + ln[end + 3:]
            in_comment = False
        ln = re.sub(r'<!--.*?-->', lambda m: ' ' * len(m.group()), ln)
        start = ln.find('<!--')
        if start >= 0:
            ln = ln[:start]
            in_comment = True
        out.append((no, ln))
    return out


def fix_text(text):
    """本文全体を修正し、(修正後テキスト, [(行番号, 修正前, 修正後)]) を返す。"""
    lines = text.split('\n')
    flags, _ = code_block_flags(lines)
    out, changes = [], []
    for no, (ln, code) in enumerate(zip(lines, flags), 1):
        if code:
            out.append(ln)
            continue
        fixed, n = fix_line(ln)
        if n:
            changes.append((no, ln.strip(), fixed.strip()))
        out.append(fixed)
    return '\n'.join(out), changes


def outside_fence(lines):
    flags, _ = code_block_flags(lines)
    return [(i, ln) for i, (ln, code) in enumerate(zip(lines, flags), 1) if not code]


def blank_fences(lines):
    """フェンスコードブロックの行を空行に置き換える(行番号は保つ)。"""
    flags, _ = code_block_flags(lines)
    return ['' if code else ln for ln, code in zip(lines, flags)]


# ---------------------------------------------------------------------------
# 見出しのアンカー
#
# GitHubは、見出しのアンカーをgithub-sluggerで作る。github-sluggerは見出しの文字列を小文字にし、
# 下記slug_removedの文字を取り除き、半角スペースをハイフンに置き換える。同じアンカーが続くと末尾に-1, -2…を付ける。

def slug_removed(ch):
    """github-sluggerがアンカーを作るときに取り除く文字か。

    github-slugger 1.5の正規表現と、日本語の文書に現れる範囲(ASCII・全角記号・かな・漢字)で一致することを確かめてある。
    """
    if ch in ' -':
        return False
    cat = unicodedata.category(ch)
    if cat == 'So' and ch.lower() != ch.upper():   # 丸囲みの英字(Ⓐ等)は残る
        return False
    return cat == 'No' or (cat[0] in 'PSZC' and cat != 'Pc')


class Slugger:
    """1文書分のアンカーを順に作る。同じアンカーには-1, -2…を付けて区別する。"""

    def __init__(self):
        self.seen = {}

    def slug(self, text):
        base = ''.join(ch for ch in text.lower() if not slug_removed(ch)).replace(' ', '-')
        slug = base
        while slug in self.seen:
            self.seen[base] += 1
            slug = '%s-%d' % (base, self.seen[base])
        self.seen[slug] = 0
        return slug


ATX_HEADING = re.compile(r'^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$')
EXPLICIT_ID = re.compile(r'[ \t]*\{#([^}\s]+)\}$')


def code_content(s):
    """インラインコードの中身を返す。前後に空白が1つずつあれば取り除く(CommonMarkの規則)。"""
    if len(s) >= 2 and s[0] == ' ' and s[-1] == ' ' and s.strip():
        return s[1:-1]
    return s


def heading_text(raw):
    """見出しのMarkdownから、画面に表示される文字列を取り出す。"""
    keep = []

    def protect(s):
        keep.append(s)
        return '\x00%d\x00' % (len(keep) - 1)

    t = re.sub(r'(`+)(.+?)\1', lambda m: protect(code_content(m.group(2))), raw)
    t = re.sub(r'\\([!-/:-@\[-`{-~])', lambda m: protect(m.group(1)), t)      # エスケープした記号
    t = re.sub(r'!?\[([^\]]*)\](?:\([^)]*\)|\[[^\]]*\])', r'\1', t)           # リンク・画像は表示文字列だけ残す
    t = re.sub(r'<[^>]+>', '', t)                                             # HTMLタグ
    t = t.replace('*', '')                                                    # 強調記法
    t = re.sub(r'(?<![^\W_])_+|_+(?![^\W_])', '', t)                          # 単語の端の`_`は強調記法
    t = re.sub(r'\x00(\d+)\x00', lambda m: keep[int(m.group(1))], t)
    return t.strip()


def heading_slugs(lines):
    """見出しを (行番号, アンカー) で返す。"""
    slugger, out = Slugger(), []
    for no, ln in content_lines(lines):
        m = ATX_HEADING.match(ln)
        if not m:
            continue
        text = re.sub(r'(?:^|[ \t]+)#+$', '', m.group(2) or '')   # 閉じの`#`
        explicit = EXPLICIT_ID.search(text)
        if explicit:
            slugger.seen[explicit.group(1)] = 0
            out.append((no, explicit.group(1)))
        else:
            out.append((no, slugger.slug(heading_text(text))))
    return out


def anchor_changes(before_lines, after_lines):
    """修正の前後で変わった見出しのアンカーを {旧: 新} で返す。"""
    before, after = heading_slugs(before_lines), heading_slugs(after_lines)
    if len(before) != len(after):
        return {}
    return {b: a for (_, b), (_, a) in zip(before, after) if b != a}


# ---------------------------------------------------------------------------
# リンク

LINK_OPEN = re.compile(r'!?\[(?:[^\[\]\\]|\\.|\[(?:[^\[\]\\]|\\.)*\])*\]\(')
REF_DEF = re.compile(r'^ {0,3}\[(?:[^\]\\]|\\.)+\]:[ \t]*(<[^>]*>|\S+)')
SCHEME = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*:')


def link_dest_span(s, i):
    """s[i]から始まるインラインリンクのリンク先を読み、(開始, 終了) を返す。リンクとして閉じていなければNoneを返す。"""
    n = len(s)
    while i < n and s[i] in ' \t':
        i += 1
    if i < n and s[i] == '<':
        j = s.find('>', i + 1)
        if j < 0:
            return None
        start, end, k = i + 1, j, j + 1
    else:
        start, depth, k = i, 0, i
        while k < n:
            c = s[k]
            if c == '\\':
                k += 2
                continue
            if c in ' \t':
                break
            if c == '(':
                depth += 1
            elif c == ')':
                if depth == 0:
                    break
                depth -= 1
            k += 1
        k = min(k, n)
        end = k
    while k < n and s[k] in ' \t':
        k += 1
    if k < n and s[k] in '"\'(':
        j = s.find({'"': '"', "'": "'", '(': ')'}[s[k]], k + 1)
        if j < 0:
            return None
        k = j + 1
        while k < n and s[k] in ' \t':
            k += 1
    if k >= n or s[k] != ')':
        return None
    return start, end


def extract_links(lines):
    """本文中のリンク(画像と参照リンクの定義を含む)を (行番号, 開始列, 終了列, リンク先) で返す。

    コードとHTMLコメントの中は除く。
    """
    out = []
    for no, ln in content_lines(lines):
        sh = CODE_SPAN.sub(lambda m: '\x01' * len(m.group()), ln)
        m = REF_DEF.match(sh)
        if m:
            s, e = m.span(1)
            if sh[s] == '<':
                s, e = s + 1, e - 1
            out.append((no, s, e, ln[s:e]))
            continue
        for m in LINK_OPEN.finditer(sh):
            span = link_dest_span(sh, m.end())
            if span:
                out.append((no, span[0], span[1], ln[span[0]:span[1]]))
    return out


def resolve_link(src_rel, dest):
    """リンク先を (リポジトリ基準のパス, 見出しアンカー) に分ける。外部URLやプレースホルダはNoneを返す。"""
    if not dest or SCHEME.match(dest) or dest.startswith('//') or '{{' in dest:
        return None
    path, _, anchor = dest.partition('#')
    path = unquote(path.split('?', 1)[0])
    if not path:
        target = src_rel
    elif path.startswith('/'):
        target = posixpath.normpath(path.lstrip('/'))
    else:
        target = posixpath.normpath(posixpath.join(posixpath.dirname(src_rel), path))
    return target, (unquote(anchor) or None)


def is_template(rel):
    """テンプレートか。テンプレートのリンクは生成先の文書から見た相対パスのため、テンプレートの場所からは解決できない。"""
    base = posixpath.basename(rel)
    return base.startswith('template') and base.endswith('.md')


SKIP_DIR = ('.git/', 'node_modules/', 'build/', 'dist/', '.docusaurus/',
            '__pycache__/', '.pnpm-store/')


def in_scope(rel):
    """リポジトリ内のMarkdownファイルか。

    コードや設定ファイルは対象にしない。シェルの引数のように、和文と英数字の間の空白が区切りとして意味を持つことがあるため。
    """
    if rel.startswith('..') or os.path.isabs(rel):
        return False
    norm = rel.replace(os.sep, '/')
    if any(part in norm for part in SKIP_DIR):
        return False
    return norm.endswith('.md')


def read_lines(path):
    return io.open(path, encoding='utf-8').read().split('\n')


def write_lines(path, lines):
    io.open(path, 'w', encoding='utf-8').write('\n'.join(lines))


class Repo:
    """リポジトリ内のMarkdownの一覧と、パスの有無・見出しのアンカーの問い合わせを受け持つ。"""

    def __init__(self, root):
        self.root = root
        self._files = None
        self._dirs = {}
        self._slugs = {}

    def rel(self, path):
        return os.path.relpath(os.path.abspath(path), self.root).replace(os.sep, '/')

    def markdown_files(self):
        """リポジトリ内のMarkdownを返す。gitが使えれば.gitignoreで除外したものを含めない。"""
        if self._files is None:
            try:
                out = subprocess.run(
                    ['git', '-C', self.root, 'ls-files', '-co', '--exclude-standard', '-z', '--', '*.md'],
                    capture_output=True, check=True).stdout.decode('utf-8')
                rels = [p for p in out.split('\0') if p]
            except (OSError, subprocess.CalledProcessError):
                rels = []
                for d, _, names in os.walk(self.root):
                    rels.extend(self.rel(os.path.join(d, n)) for n in names)
            self._files = sorted(r for r in set(rels)
                                 if in_scope(r) and os.path.isfile(os.path.join(self.root, r)))
        return self._files

    def _listdir(self, d):
        if d not in self._dirs:
            try:
                self._dirs[d] = {unicodedata.normalize('NFC', n): n for n in os.listdir(d)}
            except OSError:
                self._dirs[d] = None
        return self._dirs[d]

    def exists(self, rel):
        """リポジトリ内にパスがあるか。大文字小文字を区別する(CIのLinuxと同じ判定にするため)。"""
        if rel in ('', '.'):
            return True
        cur = self.root
        for part in rel.split('/'):
            names = self._listdir(cur)
            hit = names and names.get(unicodedata.normalize('NFC', part))
            if not hit:
                return False
            cur = os.path.join(cur, hit)
        return True

    def slugs(self, rel):
        if rel not in self._slugs:
            path = os.path.join(self.root, rel)
            self._slugs[rel] = ({s for _, s in heading_slugs(read_lines(path))}
                                if os.path.isfile(path) else set())
        return self._slugs[rel]

    def set_slugs(self, rel, lines):
        self._slugs[rel] = {s for _, s in heading_slugs(lines)}


def link_problem(repo, src_rel, dest):
    """リンク先の問題を文で返す。問題が無ければNoneを返す。"""
    r = resolve_link(src_rel, dest)
    if not r:
        return None
    target, anchor = r
    if target == '..' or target.startswith('../'):
        return 'リポジトリの外を指している'
    if not repo.exists(target):
        return 'リンク先が無い'
    if anchor and target.endswith('.md') and os.path.isfile(os.path.join(repo.root, target)):
        if anchor not in repo.slugs(target):
            return '見出し「#%s」が無い' % anchor
    return None


def check_outgoing(repo, rel, lines):
    """このファイルから出ていくリンクの切れを検出する。"""
    hits = []
    for no, _, _, dest in extract_links(lines):
        problem = link_problem(repo, rel, dest)
        if problem:
            hits.append((no, '%s: %s' % (dest, problem)))
    return hits


def check_incoming(repo, rel):
    """ほかのファイルからこのファイルの見出しへ入ってくるリンクの切れを検出する。"""
    hits, slugs = [], repo.slugs(rel)
    for other in repo.markdown_files():
        if other == rel or is_template(other):
            continue
        for no, _, _, dest in extract_links(read_lines(os.path.join(repo.root, other))):
            r = resolve_link(other, dest)
            if r and r[0] == rel and r[1] and r[1] not in slugs:
                hits.append(('%s:L%d' % (other, no), '%s: 見出し「#%s」が無い' % (dest, r[1])))
    return hits


def rewrite_anchor_links(repo, target_rel, mapping):
    """target_relの見出しのアンカーがmapping({旧: 新})のとおり変わったとき、そこへのリンクを書き換える。

    書き換えた箇所を ('ファイル:L行番号', 旧リンク先, 新リンク先) で返す。
    """
    updated = []
    for rel in repo.markdown_files():
        if is_template(rel):
            continue
        path = os.path.join(repo.root, rel)
        lines = read_lines(path)
        edits = []
        for no, s, e, dest in extract_links(lines):
            r = resolve_link(rel, dest)
            if not r or r[0] != target_rel or r[1] not in mapping:
                continue
            base, _, raw = dest.partition('#')
            new = mapping[r[1]]
            if '%' in raw:   # 元がパーセントエンコードなら合わせる
                new = quote(new, safe='')
            edits.append((no, s, e, dest, base + '#' + new))
        if not edits:
            continue
        for no, s, e, _, new_dest in sorted(edits, reverse=True):
            lines[no - 1] = lines[no - 1][:s] + new_dest + lines[no - 1][e:]
        write_lines(path, lines)
        updated.extend(('%s:L%d' % (rel, no), old, new) for no, _, _, old, new in edits)
    return updated


# ---------------------------------------------------------------------------
# フォーマットの検出

def check_html_comment(raw_lines):
    lines = blank_fences(raw_lines)
    hits, i, n = [], 0, len(lines)
    while i < n:
        pos = lines[i].find('<!--')
        if pos < 0:
            i += 1
            continue
        if '-->' in lines[i][pos + 4:]:
            i += 1
            continue
        j, close = i + 1, -1
        while j < n:
            if '-->' in lines[j]:
                close = j
                break
            if '<!--' in lines[j]:
                break
            j += 1
        if close < 0:
            hits.append((i + 1, 'HTMLコメントが閉じられていない'))
            i += 1
            continue
        k = close + 1
        while k < n and k <= close + 40:
            if '<!--' in lines[k]:
                break
            if lines[k].strip() == '-->':
                hits.append((close + 1, 'コメント本文中の`-->`でコメントが早期に閉じている'))
                break
            k += 1
        i = close + 1
    return hits


def is_space(ch):
    """空白か。行頭・行末(空文字)も空白と同じ扱いにする。"""
    return not ch or ch.isspace()


def check_emphasis(lines):
    """太字にならない強調記法を検出する。条件はBOLD_CLOSE手前のコメント参照。"""
    hits = []
    for no, ln in outside_fence(lines):
        sh = shadow(ln)
        runs = list(re.finditer(r'\*{2,}', sh))
        # 個数が奇数の行はペアを特定できないため判定しない(誤検出を避ける)
        if not runs or len(runs) % 2:
            continue
        for k, m in enumerate(runs):
            prev = sh[m.start() - 1] if m.start() > 0 else ''
            nxt = sh[m.end():m.end() + 1]
            if k % 2 == 0:      # 開き側: 内側=直後、外側=直前
                ok = (not is_space(nxt)
                      and (not is_punct(nxt) or is_space(prev) or is_punct(prev)))
            else:               # 閉じ側: 内側=直前、外側=直後
                ok = (not is_space(prev)
                      and (not is_punct(prev) or is_space(nxt) or is_punct(nxt)))
            if not ok:
                hits.append((no, '`%s`の外側に空白が要る: %s'
                             % (m.group(0), ln.strip()[:80])))
                break
    return hits


DELIM_ROW = re.compile(r'^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$')


def count_cells(row):
    """表の行のセル数を返す。`\\|`以外の`|`はインラインコードの中でもセルの区切りになる(GFMの規則)。"""
    s = row.strip().replace('\\|', '')
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|'):
        s = s[:-1]
    return s.count('|') + 1


def check_tables(lines):
    """表の列数の不一致を検出する。列数が見出し行と違う行は、セルが欠けるか、はみ出したセルが表示されない。"""
    hits, rows, i = [], content_lines(lines), 0
    while i < len(rows) - 1:
        (no, head), (no2, delim) = rows[i], rows[i + 1]
        if not ('|' in head and '|' in delim and no2 == no + 1 and DELIM_ROW.match(delim)):
            i += 1
            continue
        cols = count_cells(delim)
        if count_cells(head) != cols:
            hits.append((no, '見出し行と区切り行の列数が違う(%d列/%d列)。表として表示されない'
                         % (count_cells(head), cols)))
        j = i + 2
        while j < len(rows) and rows[j][0] == rows[j - 1][0] + 1 and rows[j][1].strip().startswith('|'):
            n = count_cells(rows[j][1])
            if n != cols:
                hits.append((rows[j][0], '%d列ある(見出し行は%d列)。`|`をセルに書くなら`\\|`にする'
                             % (n, cols)))
            j += 1
        i = j
    return hits


def check_placeholder(lines):
    return [(no, ln.strip()) for no, ln in outside_fence(lines)
            if '{{' in shadow(ln)]


def check_id_format(lines):
    hits = []
    for no, ln in outside_fence(lines):
        m = PAT_ROW.match(ln)
        if not m:
            continue
        cell = m.group(1)
        if PAT_ID_NOHYPHEN.match(cell):
            hits.append((no, '%s: 成果物略号とカテゴリ/連番をハイフンで区切る' % cell))
        elif PAT_ID_LOWER.match(cell):
            hits.append((no, '%s: IDの英字は大文字で書く' % cell))
    return hits


def render(title, ref, hits, limit=MAX_REPORT):
    body = ['[%s] %s (%d件)' % (ref, title, len(hits))]
    for where, text in hits[:limit]:
        label = 'L%d' % where if isinstance(where, int) else where
        body.append('  %s: %s' % (label, text[:160]))
    if len(hits) > limit:
        body.append('  ... ほか%d件' % (len(hits) - limit))
    return '\n'.join(body)


def inspect(repo, rel, lines, incoming=False, limit=MAX_REPORT):
    """自動修正できない問題を検出し、報告文のリストを返す。"""
    reports = []

    def add(title, ref, hits):
        if hits:
            reports.append(render(title, ref, hits, limit))

    _, unclosed = code_block_flags(lines)
    add('コードブロックが閉じられていない。以降がすべてコードとして表示される', 'Markdown',
        [(unclosed, 'ここで開いたコードブロック')] if unclosed else [])
    add('HTMLコメントの閉じ方が不正', 'CLAUDE.md §2', check_html_comment(lines))
    add('強調記法が太字にならない', 'Markdown', check_emphasis(lines))
    add('表の列数が揃っていない', 'Markdown', check_tables(lines))
    if not is_template(rel):
        add('リンク切れ', 'Markdown', check_outgoing(repo, rel, lines))
    if incoming:
        add('このファイルの見出しへのリンクが切れている', 'Markdown', check_incoming(repo, rel))
    if rel.startswith('docs/'):
        add('未置換のプレースホルダ`{{`が残っている', 'CLAUDE.md §1', check_placeholder(lines))
        add('IDの表記が規約外', 'CLAUDE.md §7', check_id_format(lines))
    return reports


# ---------------------------------------------------------------------------
# 実行

def repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def fix_file(repo, path, rel):
    """和欧間スペースを修正し、見出しのアンカーが変わったらリンクも書き換える。

    (修正内容, リンクの書き換え, 修正後の行) を返す。
    """
    src = io.open(path, encoding='utf-8').read()
    fixed, changes = fix_text(src)
    rewrites = []
    if changes:
        io.open(path, 'w', encoding='utf-8').write(fixed)
        repo.set_slugs(rel, fixed.split('\n'))
        mapping = anchor_changes(src.split('\n'), fixed.split('\n'))
        if mapping:
            rewrites = rewrite_anchor_links(repo, rel, mapping)
    lines = read_lines(path)   # 同じファイル内のリンクを書き換えた場合に備えて読み直す
    return changes, rewrites, lines


def target_paths(repo, args):
    if not args:
        return [os.path.join(repo.root, r) for r in repo.markdown_files()]
    return [p for p in args if os.path.isfile(p) and in_scope(repo.rel(p))]


def run_fix(args):
    repo = Repo(repo_root())
    total = 0
    for path in target_paths(repo, args):
        rel = repo.rel(path)
        changes, rewrites, lines = fix_file(repo, path, rel)
        total += len(changes)
        if changes:
            print('%-60s %d行を修正' % (rel, len(changes)))
        for where, old, new in rewrites:
            print('  リンクを書き換え %s: %s -> %s' % (where, old, new))
        for r in inspect(repo, rel, lines):
            print('  ! %s' % r.replace('\n', '\n  '))
    print('---\n合計%d行を修正' % total)
    return 0


def run_check(args):
    repo = Repo(repo_root())
    problems = files = 0
    for path in target_paths(repo, args):
        rel = repo.rel(path)
        src = io.open(path, encoding='utf-8').read()
        lines = src.split('\n')
        reports = inspect(repo, rel, lines, limit=10 ** 9)
        _, changes = fix_text(src)
        if changes:
            reports.insert(0, render('和欧間スペースが残っている(--fixで直る)', 'CLAUDE.md §6',
                                     [(no, after) for no, _, after in changes], 10 ** 9))
        if reports:
            files += 1
            problems += sum(int(re.search(r'\((\d+)件\)', r.split('\n')[0]).group(1)) for r in reports)
            print(rel)
            for r in reports:
                print('  ' + r.replace('\n', '\n  '))
    if problems:
        print('---\n%dファイルに%d件の問題があります' % (files, problems))
        return 1
    print('問題はありません')
    return 0


def run_hook():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    ti = payload.get('tool_input') or {}
    tr = payload.get('tool_response') or {}
    path = tr.get('filePath') or ti.get('file_path')
    if not path:
        return 0
    repo = Repo(repo_root())
    try:
        rel = repo.rel(path)
    except ValueError:
        return 0
    if not in_scope(rel) or not os.path.isfile(path):
        return 0

    try:
        changes, rewrites, lines = fix_file(repo, path, rel)
        reports = inspect(repo, rel, lines, incoming=True)
    except Exception as e:
        sys.stderr.write('lint-text-style.py: %sの検査中にエラーが発生しました: %r\n' % (rel, e))
        return 1

    notes = []
    if changes:
        detail = '\n'.join('  L%d: %s' % (no, after[:120]) for no, _, after in changes[:MAX_REPORT])
        if len(changes) > MAX_REPORT:
            detail += '\n  ... ほか%d行' % (len(changes) - MAX_REPORT)
        notes.append('%sの和欧間スペースを自動削除しました(CLAUDE.md §6・%d行)。\n'
                     'ファイルは書き換わっているため、以降の編集は最新内容を前提にしてください。\n%s'
                     % (rel, len(changes), detail))
    if rewrites:
        notes.append('見出しのアンカーが変わったため、そこへのリンクを書き換えました(%d件)。'
                     '書き換えたファイルを編集するときは、先に読み直してください。\n%s'
                     % (len(rewrites), '\n'.join('  %s: %s -> %s' % w for w in rewrites)))
    note = '\n\n'.join(notes)

    if reports:
        sys.stderr.write(
            ((note + '\n\n') if note else '')
            + '自動修正できない問題があります: %s\n\n%s\n\n'
              '該当箇所を修正してください。まだ作成していないファイルへのリンクは、作成すれば解消します。'
              '検出が誤りだと判断した場合は、自分で修正を繰り返さず、その旨をユーザーに伝えてください。\n'
            % (rel, '\n\n'.join(reports)))
        return 2

    if note:
        print(json.dumps({
            'systemMessage': '表記規約: %sを自動修正しました(和欧間スペース%d行・リンク%d件)'
                             % (rel, len(changes), len(rewrites)),
            'hookSpecificOutput': {
                'hookEventName': 'PostToolUse',
                'additionalContext': note,
            },
        }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--fix':
        sys.exit(run_fix(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        sys.exit(run_check(sys.argv[2:]))
    sys.exit(run_hook())
