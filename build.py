#!/usr/bin/env python3
"""
libc internals md → HTML 변환기.
PID html 의 변환 규칙을 그대로 따른다.

입력:  /mnt/user-data/outputs/12_libc_internals.md  (62 chapters, 7 Parts)
출력:  site/libc/part1.html ~ part7.html
       site/libc/index.html  (libc 허브)
       site/index.html       (최상위 허브)
"""

import re
import html as html_lib
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────
# Syntax Highlighting (PID 의 hl-co/fn/kw/num/str 토큰 분류)
# ─────────────────────────────────────────────────────────────────────

C_KEYWORDS = {
    'int','void','char','short','long','float','double','signed','unsigned',
    'const','volatile','static','extern','register','auto','inline','restrict',
    'struct','union','enum','typedef','sizeof','typeof','_Alignof','_Alignas',
    'if','else','while','for','do','switch','case','default','break','continue',
    'return','goto',
    '_Bool','bool','true','false','NULL','nullptr',
    '__attribute__','__asm__','__inline__','__always_inline__','__noreturn__',
    '__thread','_Thread_local','_Atomic','_Static_assert',
    'asm','__asm','__attribute',
    # POSIX-style 자주 등장
    'size_t','ssize_t','off_t','pid_t','uid_t','gid_t','time_t','mode_t',
    'uint8_t','uint16_t','uint32_t','uint64_t',
    'int8_t','int16_t','int32_t','int64_t',
    'intptr_t','uintptr_t','ptrdiff_t',
    'FILE',
}

CPP_KEYWORDS = C_KEYWORDS | {
    'class','public','private','protected','virtual','override','final',
    'namespace','using','template','typename','this','new','delete',
    'try','catch','throw','noexcept','constexpr','consteval','constinit',
    'auto','decltype','nullptr','explicit','friend','mutable','operator',
    'static_cast','dynamic_cast','const_cast','reinterpret_cast',
    'std','string','vector','map','unique_ptr','shared_ptr',
}

RUST_KEYWORDS = {
    'fn','let','mut','const','static','if','else','while','for','loop',
    'match','return','break','continue','in','as','where',
    'pub','use','mod','crate','super','self','Self',
    'struct','enum','trait','impl','type','dyn','async','await',
    'move','ref','box','unsafe','extern',
    'true','false','None','Some','Ok','Err',
    'i8','i16','i32','i64','i128','isize',
    'u8','u16','u32','u64','u128','usize',
    'f32','f64','bool','char','str','String',
    'Vec','Box','Option','Result','Rc','Arc','HashMap','BTreeMap',
}

GO_KEYWORDS = {
    'func','var','const','type','struct','interface','map','chan',
    'if','else','switch','case','default','for','range','break','continue',
    'return','go','defer','select','goto',
    'package','import',
    'nil','true','false','iota',
    'int','int8','int16','int32','int64','uint','uint8','uint16','uint32','uint64',
    'float32','float64','bool','string','byte','rune','error',
}

ASM_KEYWORDS = {
    # x86-64 instructions (자주 쓰는 것)
    'mov','movq','movl','movw','movb','movabs','movzx','movsx',
    'push','pop','call','ret','jmp','je','jne','jz','jnz','jg','jl','jge','jle','ja','jb','jae','jbe',
    'add','sub','mul','imul','div','idiv','inc','dec','neg','and','or','xor','not','shl','shr','sar',
    'cmp','test','lea','nop','int','syscall','sysenter','sysret','iret','iretq',
    'cli','sti','hlt','rep','repe','repne','cld','std',
    'leaq','addq','subq','xorq','andq','orq','testq','cmpq','negq',
    # 'long' 같은 데이터 directive
    '.byte','.word','.long','.quad','.ascii','.asciz','.section','.text','.data',
    '.global','.globl','.type','.size','.align','.p2align','.cfi_startproc','.cfi_endproc',
    # 일반 directive
    'section','global','extern','db','dw','dd','dq',
}


def escape(s: str) -> str:
    """HTML escape."""
    return html_lib.escape(s, quote=True)


def highlight_c(code: str, keywords=C_KEYWORDS) -> str:
    """C/C++ code 의 syntax highlighting (markup → escaped html with spans)."""
    # 토큰 분류용 placeholder 기반 처리
    # 순서: 주석 → 문자열 → 숫자 → keyword → function call
    
    result = []
    i = 0
    n = len(code)
    
    while i < n:
        ch = code[i]
        
        # /* ... */ 주석
        if ch == '/' and i+1 < n and code[i+1] == '*':
            end = code.find('*/', i+2)
            if end == -1:
                end = n
            else:
                end += 2
            result.append(f'<span class="hl-co">{escape(code[i:end])}</span>')
            i = end
            continue
        
        # // ... 주석
        if ch == '/' and i+1 < n and code[i+1] == '/':
            end = code.find('\n', i)
            if end == -1:
                end = n
            result.append(f'<span class="hl-co">{escape(code[i:end])}</span>')
            i = end
            continue
        
        # # ... 주석 (preprocessor) — C 의 #include 는 주석은 아니지만 우리는 hl-co 처리
        # (Bash 와 같이 처리)
        
        # 문자열 "..."
        if ch == '"':
            end = i + 1
            while end < n:
                if code[end] == '\\' and end+1 < n:
                    end += 2
                elif code[end] == '"':
                    end += 1
                    break
                else:
                    end += 1
            result.append(f'<span class="hl-str">{escape(code[i:end])}</span>')
            i = end
            continue
        
        # char literal '...'
        if ch == "'":
            end = i + 1
            while end < n:
                if code[end] == '\\' and end+1 < n:
                    end += 2
                elif code[end] == "'":
                    end += 1
                    break
                else:
                    end += 1
            # 짧은 char literal 인지 확인 (한 줄을 넘으면 string 아님)
            if end - i <= 8 and '\n' not in code[i:end]:
                result.append(f'<span class="hl-str">{escape(code[i:end])}</span>')
                i = end
                continue
            else:
                # 그냥 한 글자
                result.append(escape(ch))
                i += 1
                continue
        
        # 숫자
        if ch.isdigit() or (ch == '.' and i+1 < n and code[i+1].isdigit()):
            end = i
            while end < n and (code[end].isalnum() or code[end] in '.xXabcdefABCDEFuUlL'):
                end += 1
            result.append(f'<span class="hl-num">{escape(code[i:end])}</span>')
            i = end
            continue
        
        # identifier (keyword or function name)
        if ch.isalpha() or ch == '_':
            end = i
            while end < n and (code[end].isalnum() or code[end] == '_'):
                end += 1
            word = code[i:end]
            if word in keywords:
                result.append(f'<span class="hl-kw">{escape(word)}</span>')
            else:
                # 다음 non-space 문자가 ( 면 함수 호출
                j = end
                while j < n and code[j] == ' ':
                    j += 1
                if j < n and code[j] == '(':
                    result.append(f'<span class="hl-fn">{escape(word)}</span>')
                else:
                    result.append(escape(word))
            i = end
            continue
        
        # 그 외 (기호, 공백 등)
        result.append(escape(ch))
        i += 1
    
    return ''.join(result)


def highlight_bash(code: str) -> str:
    """Bash code highlight — $ prompt, command, string, comment."""
    lines = code.split('\n')
    out_lines = []
    for line in lines:
        out_lines.append(highlight_bash_line(line))
    return '\n'.join(out_lines)


def highlight_bash_line(line: str) -> str:
    """한 줄 단위."""
    # 전체 라인이 주석 (선행 공백 다음 # 로 시작)
    m = re.match(r'^(\s*)(#.*)$', line)
    if m:
        return escape(m.group(1)) + f'<span class="hl-co">{escape(m.group(2))}</span>'
    
    result = []
    i = 0
    n = len(line)
    in_command = True  # 첫 단어를 command 로 인식할지
    
    while i < n:
        ch = line[i]
        
        # 선행 공백
        if ch == ' ' or ch == '\t':
            end = i
            while end < n and line[end] in ' \t':
                end += 1
            result.append(escape(line[i:end]))
            i = end
            continue
        
        # $ prompt (선두에서만)
        if ch == '$' and i == 0:
            # 명령 프롬프트
            end = i + 1
            result.append(f'<span class="hl-co">{escape(line[i:end])}</span>')
            i = end
            in_command = True
            continue
        
        # # 주석
        if ch == '#':
            result.append(f'<span class="hl-co">{escape(line[i:])}</span>')
            return ''.join(result)
        
        # 문자열
        if ch == '"' or ch == "'":
            quote = ch
            end = i + 1
            while end < n:
                if line[end] == '\\' and end+1 < n:
                    end += 2
                elif line[end] == quote:
                    end += 1
                    break
                else:
                    end += 1
            result.append(f'<span class="hl-str">{escape(line[i:end])}</span>')
            i = end
            in_command = False
            continue
        
        # 숫자
        if ch.isdigit():
            end = i
            while end < n and (line[end].isalnum() or line[end] == '.'):
                end += 1
            result.append(f'<span class="hl-num">{escape(line[i:end])}</span>')
            i = end
            in_command = False
            continue
        
        # identifier
        if ch.isalpha() or ch == '_' or ch == '/' or ch == '.':
            end = i
            while end < n and (line[end].isalnum() or line[end] in '_-./'):
                end += 1
            word = line[i:end]
            if in_command and not word.startswith('-'):
                result.append(f'<span class="hl-fn">{escape(word)}</span>')
                in_command = False
            else:
                result.append(escape(word))
            i = end
            continue
        
        # | & ; 등 — 다음 토큰은 command
        if ch in '|;&':
            result.append(escape(ch))
            i += 1
            in_command = True
            continue
        
        result.append(escape(ch))
        i += 1
    
    return ''.join(result)


def highlight_asm(code: str) -> str:
    """Asm — instruction, register, comment, number."""
    lines = code.split('\n')
    out_lines = []
    for line in lines:
        out_lines.append(highlight_asm_line(line))
    return '\n'.join(out_lines)


def highlight_asm_line(line: str) -> str:
    # 전체 주석 라인
    stripped = line.lstrip()
    if stripped.startswith(('/*', '//', '#', ';')):
        return f'<span class="hl-co">{escape(line)}</span>'
    
    result = []
    i = 0
    n = len(line)
    first_token = True
    
    while i < n:
        ch = line[i]
        
        if ch in ' \t':
            end = i
            while end < n and line[end] in ' \t':
                end += 1
            result.append(escape(line[i:end]))
            i = end
            continue
        
        # 한 줄 주석 (// 또는 # 또는 ;)
        if ch == '/' and i+1 < n and line[i+1] == '/':
            result.append(f'<span class="hl-co">{escape(line[i:])}</span>')
            return ''.join(result)
        if ch == '#' or ch == ';':
            result.append(f'<span class="hl-co">{escape(line[i:])}</span>')
            return ''.join(result)
        
        # /* ... */ 주석 (한 줄 내)
        if ch == '/' and i+1 < n and line[i+1] == '*':
            end = line.find('*/', i+2)
            if end == -1:
                result.append(f'<span class="hl-co">{escape(line[i:])}</span>')
                return ''.join(result)
            end += 2
            result.append(f'<span class="hl-co">{escape(line[i:end])}</span>')
            i = end
            continue
        
        # 문자열
        if ch == '"' or ch == "'":
            quote = ch
            end = i + 1
            while end < n:
                if line[end] == '\\' and end+1 < n:
                    end += 2
                elif line[end] == quote:
                    end += 1
                    break
                else:
                    end += 1
            result.append(f'<span class="hl-str">{escape(line[i:end])}</span>')
            i = end
            continue
        
        # 숫자 (16진수 0x 포함, AT&T 의 $immediate 포함)
        if ch.isdigit() or (ch == '$' and i+1 < n and line[i+1].isdigit()):
            end = i + 1 if ch == '$' else i
            while end < n and (line[end].isalnum() or line[end] in '.x'):
                end += 1
            result.append(f'<span class="hl-num">{escape(line[i:end])}</span>')
            i = end
            continue
        
        # % register
        if ch == '%':
            end = i + 1
            while end < n and (line[end].isalnum() or line[end] == '_'):
                end += 1
            result.append(f'<span class="hl-kw">{escape(line[i:end])}</span>')
            i = end
            continue
        
        # identifier
        if ch.isalpha() or ch == '_' or ch == '.':
            end = i
            while end < n and (line[end].isalnum() or line[end] in '_.'):
                end += 1
            word = line[i:end]
            wl = word.lower()
            if wl in ASM_KEYWORDS or word in ASM_KEYWORDS:
                result.append(f'<span class="hl-kw">{escape(word)}</span>')
            elif first_token and not word.startswith('.') and not word.endswith(':'):
                # 첫 토큰이 모르는 instruction
                result.append(f'<span class="hl-fn">{escape(word)}</span>')
            else:
                result.append(escape(word))
            first_token = False
            i = end
            continue
        
        result.append(escape(ch))
        i += 1
    
    return ''.join(result)


def highlight_code(code: str, lang: str) -> str:
    """언어별 highlighting dispatcher."""
    if lang == 'c':
        return highlight_c(code, C_KEYWORDS)
    elif lang == 'cpp' or lang == 'c++':
        return highlight_c(code, CPP_KEYWORDS)
    elif lang == 'rust':
        return highlight_c(code, RUST_KEYWORDS)
    elif lang == 'go':
        return highlight_c(code, GO_KEYWORDS)
    elif lang == 'bash' or lang == 'sh' or lang == 'shell':
        return highlight_bash(code)
    elif lang == 'asm' or lang == 'x86asm' or lang == 'nasm':
        return highlight_asm(code)
    else:
        # text 또는 unknown
        return escape(code)


# ─────────────────────────────────────────────────────────────────────
# Inline markdown 처리
# ─────────────────────────────────────────────────────────────────────

def render_inline(text: str) -> str:
    """`code`, **bold**, escape 등을 처리한 HTML."""
    # 1. 코드 인라인 (backtick) 먼저 — backtick 안의 ** 는 보존
    parts = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == '`':
            # backtick 의 개수 (1 또는 2)
            cnt = 0
            while i + cnt < n and text[i+cnt] == '`':
                cnt += 1
            end = text.find('`' * cnt, i + cnt)
            if end == -1:
                # 닫는 게 없으면 그냥 escape
                parts.append(escape(text[i:i+cnt]))
                i += cnt
                continue
            inner = text[i+cnt:end]
            parts.append(f'<code class="inline-code">{escape(inner)}</code>')
            i = end + cnt
        else:
            # 다음 backtick 까지의 일반 텍스트
            next_bt = text.find('`', i)
            if next_bt == -1:
                next_bt = n
            chunk = text[i:next_bt]
            # chunk 안에서 ** 처리
            chunk = process_bold(chunk)
            parts.append(chunk)
            i = next_bt
    return ''.join(parts)


def process_bold(chunk: str) -> str:
    """**bold** 처리. chunk 는 backtick 이 없는 텍스트."""
    # **...** → <strong>...</strong> (greedy 회피, 최소 매칭)
    result = []
    i = 0
    n = len(chunk)
    while i < n:
        if i+1 < n and chunk[i:i+2] == '**':
            end = chunk.find('**', i+2)
            if end != -1:
                inner = chunk[i+2:end]
                inner_escaped = escape(inner)
                result.append(f'<strong>{inner_escaped}</strong>')
                i = end + 2
                continue
        # 일반 문자
        result.append(escape(chunk[i]))
        i += 1
    return ''.join(result)


# ─────────────────────────────────────────────────────────────────────
# Block markdown 처리
# ─────────────────────────────────────────────────────────────────────

def slug(text: str) -> str:
    """Heading ID 생성. PID 와 같은 방식."""
    # 1. 한글/영숫자/하이픈/언더스코어만 남기기
    # 2. 공백 → -
    # 3. 특수문자 제거
    # 4. 소문자
    s = text.lower()
    # 코드/강조 마크다운 제거
    s = re.sub(r'`([^`]*)`', r'\1', s)
    s = re.sub(r'\*\*([^*]*)\*\*', r'\1', s)
    # 영문 기호 → 공백
    s = re.sub(r'[^\w\s가-힣-]', ' ', s)
    # 공백 → 하이픈
    s = re.sub(r'\s+', '-', s.strip())
    # 다중 하이픈 → 단일
    s = re.sub(r'-+', '-', s)
    return s.strip('-')


def render_part(part_md: str, part_meta: dict) -> tuple[str, list[dict]]:
    """
    한 Part 의 md 를 body HTML 로 변환.
    반환: (body_html, toc_items)
      toc_items: [{'num': '1', 'title': '...', 'id': '...', 'label': '...'}, ...]
    """
    lines = part_md.split('\n')
    out = []
    toc_items = []
    i = 0
    n = len(lines)
    
    # Part 첫 줄 (# Part X. ...) 처리
    if n > 0 and lines[0].startswith('# Part '):
        m = re.match(r'^# Part ([IVXLC]+)\. (.*)$', lines[0])
        if m:
            part_label = f'Part {m.group(1)}'
            part_title = render_inline(m.group(2))
            out.append(
                f'<h1 class="stage-heading" id="{slug(lines[0][2:])}">'
                f'<span class="stage-label">{part_label}</span>'
                f'<span class="stage-title">{part_title}</span>'
                f'</h1>'
            )
            i = 1
    
    # 나머지 line 처리
    while i < n:
        line = lines[i]
        
        # 빈 줄
        if not line.strip():
            i += 1
            continue
        
        # 수평선
        if line.strip() == '---':
            out.append('<hr>')
            i += 1
            continue
        
        # ## 챕터 헤딩
        m = re.match(r'^## (\d+)\. (.*)$', line)
        if m:
            num = m.group(1)
            title_md = m.group(2)
            title_html = render_inline(title_md)
            full_text = f'{num}. {title_md}'
            sid = slug(full_text)
            out.append(
                f'<h2 class="section-heading" id="{sid}">'
                f'<span class="section-num">{num}</span>'
                f'<span class="section-title">{title_html}</span>'
                f'</h2>'
            )
            # TOC 에 추가 (label 은 일단 title 그대로, 후처리에서 줄임)
            toc_items.append({
                'num': num,
                'title': title_md,
                'id': sid,
                'label': make_short_label(title_md),
            })
            i += 1
            continue
        
        # ### 서브헤딩
        m = re.match(r'^### (.*)$', line)
        if m:
            title_md = m.group(1)
            title_html = render_inline(title_md)
            sid = slug(title_md)
            out.append(f'<h3 id="{sid}">{title_html}</h3>')
            i += 1
            continue
        
        # #### 서브-서브
        m = re.match(r'^#### (.*)$', line)
        if m:
            title_md = m.group(1)
            title_html = render_inline(title_md)
            out.append(f'<h4>{title_html}</h4>')
            i += 1
            continue
        
        # 코드블록
        m = re.match(r'^```(\w*)$', line)
        if m:
            lang = m.group(1).lower() if m.group(1) else 'text'
            code_lines = []
            i += 1
            while i < n and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            code = '\n'.join(code_lines)
            highlighted = highlight_code(code, lang)
            # text 는 lang-text 그대로 (PID 와 일치)
            out.append(
                f'<pre class="code-block lang-{lang}"><code>{highlighted}</code></pre>'
            )
            i += 1  # closing ``` 건너뜀
            continue
        
        # 인용 (>)
        if line.startswith('>'):
            # 연속된 인용 모두 모으기
            quote_lines = []
            while i < n and (lines[i].startswith('>') or lines[i].strip() == ''):
                if lines[i].startswith('>'):
                    # > 와 그 뒤 공백 제거
                    inner = lines[i][1:]
                    if inner.startswith(' '):
                        inner = inner[1:]
                    quote_lines.append(inner)
                else:
                    # 빈 줄: 인용 안에 빈 줄이 있을 수 있음. 그러나 그 다음이 인용이 아니면 중단.
                    if i+1 < n and lines[i+1].startswith('>'):
                        quote_lines.append('')
                    else:
                        break
                i += 1
            quote_md = '\n'.join(quote_lines)
            quote_body, _ = render_part(quote_md, part_meta={})
            out.append(f'<blockquote>{quote_body}</blockquote>')
            continue
        
        # 표
        if line.startswith('|') and i+1 < n and lines[i+1].startswith('|') and '---' in lines[i+1]:
            # 표 시작
            header_line = line
            i += 2  # header + separator 건너뜀
            rows = []
            while i < n and lines[i].startswith('|'):
                rows.append(lines[i])
                i += 1
            out.append(render_table(header_line, rows))
            continue
        
        # 리스트 (-)
        if line.startswith('- ') or line.startswith('* '):
            list_items = []
            while i < n and (lines[i].startswith('- ') or lines[i].startswith('* ') or lines[i].startswith('  ')):
                if lines[i].startswith(('- ', '* ')):
                    list_items.append(lines[i][2:])
                else:
                    # 계속 이어지는 줄
                    if list_items:
                        list_items[-1] += ' ' + lines[i].strip()
                i += 1
            items_html = ''.join(f'<li>{render_inline(item)}</li>' for item in list_items)
            out.append(f'<ul>{items_html}</ul>')
            continue
        
        # 일반 단락
        para_lines = [line]
        i += 1
        while i < n and lines[i].strip() and not is_block_start(lines[i]):
            para_lines.append(lines[i])
            i += 1
        para_text = ' '.join(para_lines)
        out.append(f'<p>{render_inline(para_text)}</p>')
    
    return '\n'.join(out), toc_items


def is_block_start(line: str) -> bool:
    """해당 줄이 새 블록의 시작이면 True."""
    if not line:
        return True
    if line.startswith(('#', '```', '>', '- ', '* ', '|', '---')):
        return True
    return False


def render_table(header_line: str, rows: list[str]) -> str:
    """| a | b | 형식의 표 처리."""
    def split_cells(ln):
        cells = [c.strip() for c in ln.split('|')]
        # 양 끝의 빈 cell 제거
        if cells and cells[0] == '':
            cells = cells[1:]
        if cells and cells[-1] == '':
            cells = cells[:-1]
        return cells
    
    headers = split_cells(header_line)
    body_rows = [split_cells(r) for r in rows]
    
    thead = '<thead><tr>' + ''.join(f'<th>{render_inline(h)}</th>' for h in headers) + '</tr></thead>'
    tbody_rows = []
    for row in body_rows:
        tbody_rows.append('<tr>' + ''.join(f'<td>{render_inline(c)}</td>' for c in row) + '</tr>')
    tbody = '<tbody>' + ''.join(tbody_rows) + '</tbody>'
    return f'<table>{thead}{tbody}</table>'


def make_short_label(title: str) -> str:
    """챕터 제목을 사이드바용 짧은 라벨로 변환. PID 스타일."""
    # 인라인 코드/강조 마크다운 제거
    t = re.sub(r'`([^`]*)`', r'\1', title)
    t = re.sub(r'\*\*([^*]*)\*\*', r'\1', t)
    
    # — 앞부분 또는 - 앞부분 우선 사용 (대부분 핵심)
    # 그러나 매우 짧으면 그대로
    if len(t) <= 18:
        return t
    
    # "— " 로 분리되면 앞부분
    if ' — ' in t:
        first = t.split(' — ')[0].strip()
        if 4 <= len(first) <= 22:
            return first
    
    # ": " 로 분리되면 뒷부분 (예: "오해 1: ..." → "...")
    if ': ' in t:
        last = t.split(': ', 1)[1].strip()
        if 4 <= len(last) <= 22:
            return last
    
    # — 뒷부분도 시도
    if ' — ' in t:
        last = t.split(' — ', 1)[1].strip()
        if 4 <= len(last) <= 22:
            return last
    
    # 그냥 자르기
    if len(t) > 22:
        return t[:20] + '…'
    return t


# ─────────────────────────────────────────────────────────────────────
# Part 데이터
# ─────────────────────────────────────────────────────────────────────

PARTS = [
    {'num': 'I',   'roman': 'I',   'arabic': 1, 'title': '기초', 'subtitle': 'user-space 와 kernel-space 의 경계', 'chapters': '1~8장'},
    {'num': 'II',  'roman': 'II',  'arabic': 2, 'title': 'libc 의 정체', 'subtitle': '세 가지 일', 'chapters': '9~13장'},
    {'num': 'III', 'roman': 'III', 'arabic': 3, 'title': '_start 부터 main 까지', 'subtitle': 'program startup 의 깊이', 'chapters': '14~22장'},
    {'num': 'IV',  'roman': 'IV',  'arabic': 4, 'title': 'malloc 의 깊이', 'subtitle': '동적 메모리의 정체', 'chapters': '23~32장'},
    {'num': 'V',   'roman': 'V',   'arabic': 5, 'title': 'stdio 의 깊이', 'subtitle': '입출력의 정체', 'chapters': '33~42장'},
    {'num': 'VI',  'roman': 'VI',  'arabic': 6, 'title': 'pthread 의 깊이', 'subtitle': '동시성의 정체', 'chapters': '43~52장'},
    {'num': 'VII', 'roman': 'VII', 'arabic': 7, 'title': 'dynamic linker', 'subtitle': 'ld-linux.so 의 깊이', 'chapters': '53~62장'},
]


# ─────────────────────────────────────────────────────────────────────
# HTML 레이아웃
# ─────────────────────────────────────────────────────────────────────

def part_navigation(part_idx: int, location: str = 'top') -> str:
    """Part 간 navigation HTML. part_idx 는 0-based."""
    prev_link = ''
    next_link = ''
    
    if part_idx > 0:
        prev = PARTS[part_idx - 1]
        prev_link = (
            f'<a href="part{prev["arabic"]}.html" class="nav-link nav-prev" rel="prev">'
            f'<span class="nav-arrow">←</span>'
            f'<span class="nav-meta"><span class="nav-label">Part {prev["roman"]}</span>'
            f'<span class="nav-title">{prev["title"]}</span></span>'
            f'</a>'
        )
    else:
        prev_link = '<span class="nav-link nav-disabled"></span>'
    
    next_link_html = ''
    if part_idx < len(PARTS) - 1:
        nxt = PARTS[part_idx + 1]
        next_link_html = (
            f'<a href="part{nxt["arabic"]}.html" class="nav-link nav-next" rel="next">'
            f'<span class="nav-meta nav-meta-right"><span class="nav-label">Part {nxt["roman"]}</span>'
            f'<span class="nav-title">{nxt["title"]}</span></span>'
            f'<span class="nav-arrow">→</span>'
            f'</a>'
        )
    else:
        next_link_html = '<span class="nav-link nav-disabled"></span>'
    
    hub_link = '<a href="index.html" class="nav-hub">libc 허브</a>'
    
    return (
        f'<nav class="part-nav part-nav-{location}">'
        f'{prev_link}{hub_link}{next_link_html}'
        f'</nav>'
    )


def sidebar_html(part_idx: int, toc_items: list[dict]) -> str:
    """사이드바 — Part navigator + 현재 Part 의 TOC."""
    # Part navigator (1~7)
    part_nav_items = []
    for j, p in enumerate(PARTS):
        if j == part_idx:
            cls = 'part-nav-link part-nav-current'
        else:
            cls = 'part-nav-link'
        part_nav_items.append(
            f'<li><a href="part{p["arabic"]}.html" class="{cls}">'
            f'<span class="part-nav-num">Part {p["roman"]}</span>'
            f'<span class="part-nav-text">{p["title"]}</span>'
            f'</a></li>'
        )
    part_nav = (
        '<div class="sidebar-section">'
        '<div class="toc-title">Parts</div>'
        '<ul class="part-nav-list">' + ''.join(part_nav_items) + '</ul>'
        '</div>'
    )
    
    # 현재 Part 의 TOC
    toc_lis = []
    for item in toc_items:
        toc_lis.append(
            f'<li class="toc-sec"><a href="#{item["id"]}">'
            f'<span class="toc-num">{item["num"]}</span>'
            f'<span class="toc-label">{item["label"]}</span>'
            f'</a></li>'
        )
    toc_section = (
        '<div class="sidebar-section">'
        '<div class="toc-title">Contents</div>'
        '<ul class="toc-list">' + ''.join(toc_lis) + '</ul>'
        '</div>'
    )
    
    # 최상위 허브 링크
    home_link = (
        '<div class="sidebar-section sidebar-home">'
        '<a href="../index.html" class="home-link">← System Internals 홈</a>'
        '</div>'
    )
    
    return (
        '<aside class="sidebar">'
        '<nav class="toc" aria-label="목차">'
        + home_link + part_nav + toc_section +
        '</nav>'
        '</aside>'
    )


def render_part_html(part_idx: int, body_html: str, toc_items: list[dict]) -> str:
    """Part 의 완전한 HTML."""
    part = PARTS[part_idx]
    doc_title = f'libc 깊이 — Part {part["roman"]}: {part["title"]}'
    
    doc_header = (
        '<div class="doc-header">'
        '<div class="doc-eyebrow">libc internals</div>'
        f'<h1 class="doc-title">Part {part["roman"]} — {part["title"]}</h1>'
        f'<div class="doc-subtitle">{part["subtitle"]}</div>'
        f'<div class="doc-meta"><span>{part["chapters"]}</span>'
        f'<span>{len(toc_items)} chapters</span>'
        f'<span>Verified against glibc master</span></div>'
        '</div>'
    )
    
    sidebar = sidebar_html(part_idx, toc_items)
    nav_top = part_navigation(part_idx, 'top')
    nav_bottom = part_navigation(part_idx, 'bottom')
    
    return f'''<!DOCTYPE html>
<html lang="ko" data-theme="auto">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{doc_title}</title>
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>
<button id="theme-toggle" class="theme-toggle">🌙 Dark</button>
<div class="layout">
{sidebar}
<main class="content">
{nav_top}
{doc_header}
{body_html}
{nav_bottom}
</main>
</div>
<script src="../assets/script.js"></script>
</body>
</html>
'''


# ─────────────────────────────────────────────────────────────────────
# libc/index.html (libc 허브)
# ─────────────────────────────────────────────────────────────────────

def render_libc_hub() -> str:
    """libc 허브 — 7개 Part 카드."""
    cards = []
    for p in PARTS:
        cards.append(
            f'<a href="part{p["arabic"]}.html" class="part-card">'
            f'<div class="part-card-label">Part {p["roman"]}</div>'
            f'<div class="part-card-title">{p["title"]}</div>'
            f'<div class="part-card-subtitle">{p["subtitle"]}</div>'
            f'<div class="part-card-meta">{p["chapters"]}</div>'
            f'</a>'
        )
    cards_html = '<div class="part-cards">' + ''.join(cards) + '</div>'
    
    home_link = '<div class="hub-home"><a href="../index.html">← System Internals 홈</a></div>'
    
    doc_header = (
        '<div class="doc-header">'
        '<div class="doc-eyebrow">Technical Deep Dive</div>'
        '<h1 class="doc-title">libc 깊이 이해</h1>'
        '<div class="doc-subtitle">C 라이브러리부터 언어 runtime 까지 — 62 chapters, 7 Parts</div>'
        '<div class="doc-meta"><span>30,359 lines</span><span>62 chapters</span><span>Verified against glibc master</span></div>'
        '</div>'
    )
    
    intro = '''
<p>이 문서는 libc 의 내부 동작을 7개 Part 로 나누어 정리한 학습 가이드다. user-space 와 kernel-space 의 경계에서 시작해, libc 의 정체, program startup, 동적 메모리, 표준 입출력, 동시성, 그리고 마지막으로 dynamic linker 까지 — 각 주제를 공식 소스 (glibc master, musl, Linux kernel) 의 검증된 사실로 풀어간다.</p>
<p>각 Part 는 독립된 HTML 문서다. 순서대로 읽어도 좋고, 관심 있는 주제부터 펼쳐도 된다.</p>
'''
    
    return f'''<!DOCTYPE html>
<html lang="ko" data-theme="auto">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>libc 깊이 이해 — 7개 Part 학습 가이드</title>
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>
<button id="theme-toggle" class="theme-toggle">🌙 Dark</button>
<main class="content content-hub">
{home_link}
{doc_header}
{intro}
{cards_html}
</main>
<script src="../assets/script.js"></script>
</body>
</html>
'''


# ─────────────────────────────────────────────────────────────────────
# 최상위 index.html (System Internals 허브)
# ─────────────────────────────────────────────────────────────────────

def render_root_hub() -> str:
    """최상위 허브 — libc 카드 + PID 카드."""
    cards = [
        (
            '<a href="libc/index.html" class="doc-card">'
            '<div class="doc-card-label">Document 01</div>'
            '<div class="doc-card-title">libc 깊이 이해</div>'
            '<div class="doc-card-subtitle">C 라이브러리부터 언어 runtime 까지</div>'
            '<div class="doc-card-body">user-space / kernel-space 의 경계에서 시작해 libc 의 정체, program startup, malloc, stdio, pthread, dynamic linker 까지. 7개 Part 로 분할.</div>'
            '<div class="doc-card-meta">62 chapters · 7 Parts · Verified against glibc master</div>'
            '</a>'
        ),
        (
            '<a href="pid/index.html" class="doc-card">'
            '<div class="doc-card-label">Document 02</div>'
            '<div class="doc-card-title">Linux 부팅과 PID 0/1/2</div>'
            '<div class="doc-card-subtitle">단계별 학습 가이드</div>'
            '<div class="doc-card-body">Linux 커널이 부팅되어 첫 사용자 프로세스가 실행되기까지의 흐름. main 함수의 정체, start_kernel, PID 0/1/2 의 정체, PID namespace, container 의 PID 1 까지. 단일 페이지.</div>'
            '<div class="doc-card-meta">57 sections · Stage 0~7 + Appendix · Verified against kernel master</div>'
            '</a>'
        ),
    ]
    cards_html = '<div class="doc-cards">' + ''.join(cards) + '</div>'
    
    doc_header = (
        '<div class="doc-header">'
        '<div class="doc-eyebrow">Hans9500</div>'
        '<h1 class="doc-title">System Internals</h1>'
        '<div class="doc-subtitle">시스템 깊이 학습 가이드 모음</div>'
        '</div>'
    )
    
    intro = '''
<p>OS, 런타임, 그리고 시스템 라이브러리의 깊이를 — 공식 소스로 검증해 한국어로 정리한 학습 문서 모음이다. 각 문서는 독립적이고, 실제 master 브랜치의 소스 코드를 인용 / 검증한다.</p>
'''
    
    return f'''<!DOCTYPE html>
<html lang="ko" data-theme="auto">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>System Internals — 시스템 깊이 학습 가이드</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<button id="theme-toggle" class="theme-toggle">🌙 Dark</button>
<main class="content content-hub">
{doc_header}
{intro}
{cards_html}
</main>
<script src="assets/script.js"></script>
</body>
</html>
'''


# ─────────────────────────────────────────────────────────────────────
# 메인 빌드
# ─────────────────────────────────────────────────────────────────────

def main():
    SRC = Path('/mnt/user-data/outputs/12_libc_internals.md')
    OUT = Path('/home/claude/work/site')
    OUT_LIBC = OUT / 'libc'
    OUT_LIBC.mkdir(exist_ok=True, parents=True)
    
    md = SRC.read_text(encoding='utf-8')
    lines = md.split('\n')
    
    # Part 경계 찾기
    part_starts = []
    for i, line in enumerate(lines):
        if re.match(r'^# Part [IVXLC]+\. ', line):
            part_starts.append(i)
    part_starts.append(len(lines))
    
    print(f'발견된 Part 수: {len(part_starts) - 1}')
    
    # 각 Part 변환
    for idx in range(len(part_starts) - 1):
        start = part_starts[idx]
        end = part_starts[idx + 1]
        part_md = '\n'.join(lines[start:end])
        
        part = PARTS[idx]
        body_html, toc_items = render_part(part_md, part)
        full_html = render_part_html(idx, body_html, toc_items)
        
        out_path = OUT_LIBC / f'part{part["arabic"]}.html'
        out_path.write_text(full_html, encoding='utf-8')
        size_kb = out_path.stat().st_size / 1024
        print(f'  part{part["arabic"]}.html: {size_kb:.0f} KB, {len(toc_items)} chapters')
    
    # libc 허브
    (OUT_LIBC / 'index.html').write_text(render_libc_hub(), encoding='utf-8')
    print(f'libc/index.html 생성')
    
    # 최상위 허브
    (OUT / 'index.html').write_text(render_root_hub(), encoding='utf-8')
    print(f'index.html 생성')
    
    print('\n=== 빌드 완료 ===')


if __name__ == '__main__':
    main()
