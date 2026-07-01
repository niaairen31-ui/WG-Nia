$raw = [Console]::In.ReadToEnd()
try { $in = $raw | ConvertFrom-Json } catch { exit 0 }
$cmd = "$($in.tool_input.command)"
if ($cmd -match 'git\s+push' -and $cmd -match '\b(main|master)\b') {
  $out = @{ hookSpecificOutput = @{ hookEventName = "PreToolUse"
            permissionDecision = "deny"
            permissionDecisionReason = "C1: direct push to main is blocked. Use a ticket/NNNN branch + PR." } }
  $out | ConvertTo-Json -Depth 5
  exit 0
}
exit 0
