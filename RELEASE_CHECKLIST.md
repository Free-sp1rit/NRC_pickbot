# Release Checklist

## Scope

Use this checklist before every public release.

## Pre-release verification

- Confirm `flow_test.txt` covers the latest input actions.
- Confirm `flow.txt` covers the intended business flow.
- Run the target game and verify the full flow at least once.
- Verify hotkeys:
  - `F7` loads `flow_test.txt`
  - `F8` starts or stops
  - `F9` reloads the main flow
  - `F10` exits
- Verify emergency stop with the mouse in the top-left corner.
- Check `logs/pickbot.log` for unhandled exceptions.
- Confirm the release still uses input simulation and screen detection only.
- Confirm no memory read/write or injection behavior was introduced.

## Release artifacts

The public release should contain:

- `pickbot.exe`
- `config.json`
- `flow.txt`
- `USER_GUIDE.md`
- `README.md`
- `NOTICE.txt`
- `VERSION.txt`
- `SHA256SUMS.txt`

## Metadata

- Update `VERSION.txt`.
- Prepare release notes.
- Record the git commit hash for the release.
- Generate and verify `SHA256SUMS.txt`.

## Distribution

- Publish only through the official channel.
- Include the free-of-charge statement.
- Include checksum verification instructions.
- Keep the previous release available for rollback.

## Support rules

- Only support official builds.
- Require users to provide:
  - version
  - commit hash
  - `logs/pickbot.log`
