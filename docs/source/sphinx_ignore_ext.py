import os
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from sphinx.ext.autodoc import between


def load_gitignore():
    gitignore_path = os.path.join(os.path.dirname(__file__), ".gitignore")
    if not os.path.exists(gitignore_path):
        print(f"Warning: .gitignore file not found at {gitignore_path}")
        return PathSpec.from_lines(GitWildMatchPattern, [])

    with open(gitignore_path, "r") as ignore_file:
        gitignore = ignore_file.read().splitlines()
    return PathSpec.from_lines(GitWildMatchPattern, gitignore)


gitignore_spec = load_gitignore()


def should_ignore(path):
    return gitignore_spec.match_file(path)


def autodoc_skip_member(app, what, name, obj, skip, options):
    if should_ignore(name):
        return True
    return skip


def setup(app):
    app.connect("autodoc-skip-member", autodoc_skip_member)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
