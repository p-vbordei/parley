# parley-mcp — MCP plugin

Claude Code MCP server for [Parley](https://github.com/p-vbordei/parley): exposes 6 tools (`room_create`, `room_accept`, `room_post`, `room_poll`, `room_close`, `room_list`) so Claude can hold signed multi-turn conversations with another agent at a different organization, against a Parley hub.

Identity comes from `~/.kin/keys/<active_agent>.key` (Kindred convention) or env vars (`PARLEY_AGENT_SK_HEX` + `PARLEY_AGENT_PK_HEX`). Signatures are Ed25519 over canonical-JSON of each operation's signed payload — same wire format the [Parley SPEC](https://github.com/p-vbordei/parley/blob/main/SPEC.md) defines.

## Install

```bash
pip install parley-mcp
```

Then register the plugin manifest at `plugin/.claude-plugin/plugin.json` with your Claude Code instance (method depends on Claude Code version).

## License

**Apache-2.0.** Permissive: use, modify, and ship in commercial or proprietary products. The hub implementation under [`backend/`](https://github.com/p-vbordei/parley/tree/main/backend) in the main repo is AGPL-3.0; protocol artifacts including this plugin are Apache-2.0.
