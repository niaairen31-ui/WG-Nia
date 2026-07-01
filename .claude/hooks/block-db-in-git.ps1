# Belt-and-suspenders. The PRIMARY defense is .gitignore (below).
$raw = [Console]::In.ReadToEnd()
try { $in = $raw | ConvertFrom-Json } catch { exit 0 }
$cmd = "$($in.tool_input.command)"
if ($cmd -match 'git\s+add' -and $cmd -match '\.db\b') {
  $out = @{ hookSpecificOutput = @{ hookEventName = "PreToolUse"
            permissionDecision = "deny"
            permissionDecisionReason = "The database must never re-enter the git tree (June 19 incident)." } }
  $out | ConvertTo-Json -Depth 5
  exit 0
}
exit 0
