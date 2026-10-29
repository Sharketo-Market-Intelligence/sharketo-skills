# Sharketo skills

Coding-agent guidance for integrating the Sharketo Python SDK into your application.

## Install the skill

Run from your application directory. For Codex:

```sh
npx skills@1.7.4 add Sharketo-Market-Intelligence/sharketo-skills --skill sharketo-python -a codex --copy
```

For Claude Code, replace `-a codex` with `-a claude-code`. These commands install a
project-local copy. Refresh your agent session if needed, then confirm it discovers
`sharketo-python`.

These commands use the tested installer `skills@1.7.4`, which requires Node.js
22.20.0 or later.

The default branch carries the latest distributed skill. To select this release explicitly:

```sh
npx skills@1.7.4 add https://github.com/Sharketo-Market-Intelligence/sharketo-skills/tree/v0.1.14b4 --skill sharketo-python -a codex --copy
```

## Let your agent install the SDK

The current skill matches SDK **0.1.14b4**, available on **production PyPI**.
Skill installation provides instructions and examples; it does not install the Python
package or grant API access.

After confirming discovery, ask your agent:

> Use the sharketo-python skill to install the matching SDK in this project's virtual
> environment, then create and run a minimal offline Sharketo example.

The [SDK installation guide](skills/sharketo-python/references/install.md) pins the
matching version on production PyPI for pip and uv. The offline quickstart needs no
Sharketo credentials or live API access.

Keep the installed skill and the application's SDK versions matched. Review local skill
edits before reinstalling or upgrading. Installing files does not establish native-host
discovery or execution; verify those in the host and version you use.

## API access and license

Live use requires authorized server-side credentials and applicable service access.
Developer personal-use restrictions and API-content terms apply separately from the
[MIT code license](LICENSE). Follow the skill's [setup guide](skills/sharketo-python/references/setup.md)
for API access; never put API keys in skill files or source code.
