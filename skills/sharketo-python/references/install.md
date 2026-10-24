# Versioned skill delivery

Skill 0.1.14b3 matches SDK 0.1.14b3, distributed as `sharketo-sdk` and imported as `sharketo`. Check the application's Python environment with `python -c 'from importlib.metadata import version; print(version("sharketo-sdk"))'`. A globally installed skill may not match the project's SDK.

## Install the SDK from an installed skill

An installed skill does not install the Python package. Use Python 3.11+ in the
application's virtual environment and install the matching SDK from PyPI:

```sh
python -m pip install --index-url https://pypi.org/simple/ sharketo-sdk==0.1.14b3
```

Use an environment without configured extra package indexes. For a uv-managed project:

```sh
uv add --default-index https://pypi.org/simple/ sharketo-sdk==0.1.14b3
```

If the matching release is unavailable on PyPI, stop and report the unavailable version.
Do not substitute another version, package index or source checkout. Installation does
not configure credentials or grant API access.

The wheel bundles the skill, references, synthetic fixtures and plugin manifests. If the
skill is already installed, continue with offline verification rather than installing a
duplicate. The commands below otherwise use the installed package.

SDK and skill code use the MIT license. The skill directory and every exported wrapper retain `LICENSE`.

## Verify the installed SDK offline

Run `python -m sharketo.quickstart` in the application's Python environment. In a uv
project, use `uv run python -m sharketo.quickstart`. It runs offline with invented
data and an in-memory HTTP transport.

## Set up API access

For portal API key creation or first-time server-side credential configuration, follow
[first-time API key setup](setup.md).

## Explicit filesystem installation

From the application project, with its SDK environment active:

```sh
python -m sharketo.skills install --agent claude-code --scope project
python -m sharketo.skills install --agent codex --scope project
```

- Claude Code installs project skills in `.claude/skills/sharketo-python/` and user skills in `~/.claude/skills/sharketo-python/`.
- Codex installs project skills in `.agents/skills/sharketo-python/` and user skills in `~/.agents/skills/sharketo-python/`. Verify discovery in the installed host and version, not by checking another host's paths.
- Select user scope with `--scope user`. Select another project with `--scope project --project /path/to/application`. The latter is invalid for user scope.
- The installer preserves existing destinations by default. Inspect local edits before approving `--force`. It replaces the entire destination, including obsolete files. The installer refuses symlink destinations or parents even with `--force`. Stop other installers before replacement. Concurrent directory modification is unsupported.
- Refresh or restart the host as needed and confirm discovery. Install either a standalone skill or a plugin copy in each host. Duplicate copies can have different invocation names and versions.

`pip install` does not register the skill automatically. If a previous installer created symlinks, inspect and remove only links you own before using the Python installer; `--force` does not replace symlink destinations.

## Keep upgrades matched

Upgrade the SDK in the application environment and inspect local skill edits. Reinstall
with `--force` only after approving a complete replacement. Confirm the SDK version and
refresh the host. A global skill can otherwise describe a different version from the project.

The PyPI installation above is pinned to 0.1.14b3. Select a published matching SDK and
skill release before changing the pin. Installing a new SDK does not update an existing
skill automatically.

## Export and native host wrappers

```sh
python -m sharketo.skills export --format skill --output ./sharketo-skill.zip
python -m sharketo.skills export --format openai-plugin --output ./sharketo-openai-plugin.zip
python -m sharketo.skills export --format claude-plugin --output ./sharketo-claude-plugin.zip
```

- ZIPs contain one `sharketo-python/` root. Standalone exports put `SKILL.md` and supporting files there. Plugins put the same content under `skills/sharketo-python/` and add a manifest. Exports refuse existing outputs unless you pass `--force`.
- The OpenAI wrapper has a root `plugin.json` using the Agent Plugins schema. Extract and register the plugin folder through a supported local marketplace or eligible workspace plugin workflow. Follow [OpenAI packaging instructions](https://developers.openai.com/plugins/build/plugins).
- The Claude wrapper has `.claude-plugin/plugin.json`. Extract and load it through the installed Claude Code host's [local plugin workflow](https://code.claude.com/docs/en/plugins). Native plugin invocation names may include a namespace. Do not assume the standalone skill name works alone.
- [OpenAI's skills guide](https://developers.openai.com/codex/skills) covers standalone desktop skills and plugin distribution. [ChatGPT availability](https://help.openai.com/en/articles/20001066-skills-in-chatgpt) depends on the account, workspace and interface.
- Verify Python execution and outbound access in the target host and mode.
