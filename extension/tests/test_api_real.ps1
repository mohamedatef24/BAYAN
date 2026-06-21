$ErrorActionPreference = 'Stop'

# Test Case 1: Basic Correction Flow
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "TEST CASE 1: Basic Correction Flow" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan

$inputText = 'انا ذهبت الي المدرسه اليوم'
Write-Host "`nInput: `"$inputText`""

$body = @{ text = $inputText } | ConvertTo-Json -Compress
$response = Invoke-RestMethod -Uri 'https://bayan10-bayan-api.hf.space/api/analyze' -Method POST -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -ContentType 'application/json; charset=utf-8'

Write-Host "`n── API Response ──" -ForegroundColor Yellow
Write-Host "Status: $($response.status)"
Write-Host "Original: `"$($response.original)`""
Write-Host "Corrected: `"$($response.corrected)`""
Write-Host "Suggestions count: $($response.suggestions.Count)"

Write-Host "`n── Timing ──" -ForegroundColor Yellow
Write-Host "Total: $($response.timing_ms.total_ms)ms"
Write-Host "Spelling: $($response.timing_ms.spelling_ms)ms"
Write-Host "Grammar: $($response.timing_ms.grammar_ms)ms"
Write-Host "Punctuation: $($response.timing_ms.punctuation_ms)ms"

Write-Host "`n── Suggestions ──" -ForegroundColor Yellow
foreach ($s in $response.suggestions) {
    Write-Host "  [$($s.type)] `"$($s.original)`" → `"$($s.correction)`"  (start:$($s.start), end:$($s.end), id:$($s.id.Substring(0,8))...)"
    if ($s.alternatives) {
        Write-Host "    Alternatives: $($s.alternatives -join ', ')"
    }
}

# Schema validation
Write-Host "`n── Schema Validation ──" -ForegroundColor Yellow
$fields = @('status', 'original', 'corrected', 'suggestions', 'timing_ms')
foreach ($f in $fields) {
    $exists = $null -ne $response.$f
    $icon = if ($exists) { "✅" } else { "❌" }
    Write-Host "  $icon Field '$f' present"
}

# Suggestion schema
if ($response.suggestions.Count -gt 0) {
    $s = $response.suggestions[0]
    $sFields = @('id', 'start', 'end', 'original', 'correction', 'type', 'alternatives')
    foreach ($f in $sFields) {
        $exists = $null -ne $s.$f
        $icon = if ($exists) { "✅" } else { "❌" }
        Write-Host "  $icon Suggestion field '$f' present"
    }
}

Write-Host "`n═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "TEST CASE 2: Sequential Apply Input" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan

$inputText2 = 'انا ذاهب الي البت'
Write-Host "`nInput: `"$inputText2`""

$body2 = @{ text = $inputText2 } | ConvertTo-Json -Compress
$response2 = Invoke-RestMethod -Uri 'https://bayan10-bayan-api.hf.space/api/analyze' -Method POST -Body ([System.Text.Encoding]::UTF8.GetBytes($body2)) -ContentType 'application/json; charset=utf-8'

Write-Host "`n── API Response ──" -ForegroundColor Yellow
Write-Host "Status: $($response2.status)"
Write-Host "Original: `"$($response2.original)`""
Write-Host "Corrected: `"$($response2.corrected)`""
Write-Host "Suggestions count: $($response2.suggestions.Count)"

Write-Host "`n── Suggestions ──" -ForegroundColor Yellow
foreach ($s in $response2.suggestions) {
    Write-Host "  [$($s.type)] `"$($s.original)`" → `"$($s.correction)`"  (start:$($s.start), end:$($s.end))"
    if ($s.alternatives) {
        Write-Host "    Alternatives: $($s.alternatives -join ', ')"
    }
}

# Save response for browser test
$response2 | ConvertTo-Json -Depth 5 | Out-File -FilePath 'e:\Atef''s Shit\extension\tests\api_response_tc2.json' -Encoding UTF8
Write-Host "`n✅ Response saved to api_response_tc2.json"
