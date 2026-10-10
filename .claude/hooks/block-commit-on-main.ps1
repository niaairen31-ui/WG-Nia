# M1 (TICKET-0117). Commits are pre-authorized, so a commit on main must be
# refused structurally: block-main-push only sees a command naming main.
# Fail-closed: a branch that cannot be read is refused too.
$raw = [Console]::In.ReadToEnd()
try { $in = $raw | ConvertFrom-Json } catch { exit 0 }
$cmd = "$($in.tool_input.command)"
if ($cmd -notmatch '\bgit\b[^;&|]*\bcommit\b') { exit 0 }
$branch = "$(git -C "$env:CLAUDE_PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>$null)".Trim()
if ($branch -eq '' -or $branch -match '^(main|master)$') {
  $out = @{ hookSpecificOutput = @{ hookEventName = "PreToolUse"
            permissionDecision = "deny"
            permissionDecisionReason = "M1: no commit on main (branch '$branch'). Switch to ticket/NNNN first." } }
  $out | ConvertTo-Json -Depth 5
  exit 0
}
exit 0
