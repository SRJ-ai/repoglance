"""Extension-to-language mapping and language color hints."""
from __future__ import annotations

# Map file extension (lowercase, no dot) -> language name.
EXT_LANG = {
    "py": "Python",
    "pyi": "Python",
    "js": "JavaScript",
    "mjs": "JavaScript",
    "cjs": "JavaScript",
    "jsx": "JavaScript",
    "ts": "TypeScript",
    "tsx": "TypeScript",
    "go": "Go",
    "rs": "Rust",
    "java": "Java",
    "kt": "Kotlin",
    "c": "C",
    "h": "C",
    "cpp": "C++",
    "cc": "C++",
    "cxx": "C++",
    "hpp": "C++",
    "cs": "C#",
    "rb": "Ruby",
    "php": "PHP",
    "swift": "Swift",
    "m": "Objective-C",
    "scala": "Scala",
    "sh": "Shell",
    "bash": "Shell",
    "zsh": "Shell",
    "ps1": "PowerShell",
    "lua": "Lua",
    "r": "R",
    "dart": "Dart",
    "ex": "Elixir",
    "exs": "Elixir",
    "erl": "Erlang",
    "clj": "Clojure",
    "hs": "Haskell",
    "ml": "OCaml",
    "sql": "SQL",
    "html": "HTML",
    "htm": "HTML",
    "css": "CSS",
    "scss": "SCSS",
    "sass": "Sass",
    "less": "Less",
    "vue": "Vue",
    "svelte": "Svelte",
    "json": "JSON",
    "yaml": "YAML",
    "yml": "YAML",
    "toml": "TOML",
    "xml": "XML",
    "md": "Markdown",
    "rst": "reStructuredText",
    "tex": "TeX",
    "proto": "Protobuf",
    "graphql": "GraphQL",
    "tf": "Terraform",
    "dockerfile": "Dockerfile",
    "makefile": "Makefile",
    "cmake": "CMake",
    "gradle": "Gradle",
    "vim": "Vim script",
    "asm": "Assembly",
    "s": "Assembly",
}

# Stable-ish display color per language (rich color names / hex).
LANG_COLOR = {
    "Python": "#3572A5",
    "JavaScript": "#F1E05A",
    "TypeScript": "#3178C6",
    "Go": "#00ADD8",
    "Rust": "#DEA584",
    "Java": "#B07219",
    "C": "#555555",
    "C++": "#F34B7D",
    "C#": "#178600",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Swift": "#F05138",
    "Shell": "#89E051",
    "HTML": "#E34C26",
    "CSS": "#563D7C",
    "Vue": "#41B883",
    "Markdown": "#083FA1",
    "JSON": "#CB9800",
    "YAML": "#CB171E",
}

DEFAULT_COLOR = "#8B949E"


def lang_for(ext: str, filename: str) -> str:
    """Resolve a language from extension, falling back to well-known filenames."""
    name = filename.lower()
    if name in ("makefile", "gnumakefile"):
        return "Makefile"
    if name.startswith("dockerfile"):
        return "Dockerfile"
    if name == "cmakelists.txt":
        return "CMake"
    return EXT_LANG.get(ext.lower(), "")


def color_for(language: str) -> str:
    return LANG_COLOR.get(language, DEFAULT_COLOR)
