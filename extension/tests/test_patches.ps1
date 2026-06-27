# Bayan Patch Engine Tests — PowerShell Runner
# Evaluates the JavaScript test logic without Node.js

$passed = 0
$failed = 0

function Assert-Equal($actual, $expected, $message) {
    if ($actual -eq $expected) {
        $script:passed++
        Write-Host "  ✅ $message" -ForegroundColor Green
    } else {
        $script:failed++
        Write-Host "  ❌ $message" -ForegroundColor Red
        Write-Host "     Expected: `"$expected`"" -ForegroundColor DarkGray
        Write-Host "     Actual:   `"$actual`"" -ForegroundColor DarkGray
    }
}

function Assert-True($condition, $message) {
    if ($condition) {
        $script:passed++
        Write-Host "  ✅ $message" -ForegroundColor Green
    } else {
        $script:failed++
        Write-Host "  ❌ $message" -ForegroundColor Red
    }
}

# ── Simulate applyAndRebase in PowerShell ──
function ApplyAndRebase($text, $applied, $replacement, $suggestions) {
    # Apply patch
    $newText = $text.Substring(0, $applied.start) + $replacement + $text.Substring($applied.end)

    # Calculate delta
    $originalSpanLength = $applied.end - $applied.start
    $delta = $replacement.Length - $originalSpanLength

    # Remove applied and rebase
    $rebased = @()
    foreach ($s in $suggestions) {
        if ($s.id -eq $applied.id) { continue }
        if ($s.start -ge $applied.end) {
            $rebased += @{
                id = $s.id; start = $s.start + $delta; end = $s.end + $delta
                original = $s.original; correction = $s.correction; type = $s.type
            }
        } else {
            $rebased += $s
        }
    }

    return @{ text = $newText; suggestions = $rebased }
}

function ApplyAllPatches($text, $suggestions) {
    $sorted = $suggestions | Sort-Object { $_.start } -Descending
    $result = $text
    foreach ($s in $sorted) {
        $result = $result.Substring(0, $s.start) + $s.correction + $result.Substring($s.end)
    }
    return $result
}

# ── Test Data ──
$TEXT = 'أنا ذاهب الى البت والمدرسه'

function MakeSuggestions {
    return @(
        @{ id='a'; start=10; end=13; original='الى'; correction='إلى'; type='grammar' },
        @{ id='b'; start=14; end=17; original='البت'; correction='البيت'; type='spelling' },
        @{ id='c'; start=19; end=26; original='المدرسه'; correction='المدرسة'; type='spelling' }
    )
}

# ══════════════════════════════════════════════════════════
# TEST 1: Same-length replacement (delta = 0)
# ══════════════════════════════════════════════════════════
Write-Host "`n── TEST 1: Same-length replacement (delta = 0) ──" -ForegroundColor Cyan
$suggestions = MakeSuggestions
$result = ApplyAndRebase $TEXT $suggestions[0] 'إلى' $suggestions
Assert-Equal $result.text 'أنا ذاهب إلى البت والمدرسه' 'Text: الى → إلى'
Assert-True ($result.suggestions.Count -eq 2) 'Removed applied suggestion (2 remaining)'
Assert-Equal $result.suggestions[0].start 14 'Suggestion B start unchanged (14)'
Assert-Equal $result.suggestions[0].end 17 'Suggestion B end unchanged (17)'
Assert-Equal $result.suggestions[1].start 19 'Suggestion C start unchanged (19)'
Assert-Equal $result.suggestions[1].end 26 'Suggestion C end unchanged (26)'

# ══════════════════════════════════════════════════════════
# TEST 2: Longer replacement (delta > 0)
# ══════════════════════════════════════════════════════════
Write-Host "`n── TEST 2: Longer replacement (delta > 0) ──" -ForegroundColor Cyan
$suggestions = MakeSuggestions
$result = ApplyAndRebase $TEXT $suggestions[1] 'البيت' $suggestions
Assert-Equal $result.text 'أنا ذاهب الى البيت والمدرسه' 'Text: البت → البيت'
Assert-True ($result.suggestions.Count -eq 2) 'Removed applied suggestion (2 remaining)'
Assert-Equal $result.suggestions[0].start 10 'Suggestion A start unchanged (10)'
Assert-Equal $result.suggestions[0].end 13 'Suggestion A end unchanged (13)'
Assert-Equal $result.suggestions[1].start 21 'Suggestion C start shifted 19→21 (+2)'
Assert-Equal $result.suggestions[1].end 28 'Suggestion C end shifted 26→28 (+2)'
$extracted = $result.text.Substring($result.suggestions[1].start, $result.suggestions[1].end - $result.suggestions[1].start)
Assert-Equal $extracted 'المدرسه' 'Rebased offset C extracts correct text'

# ══════════════════════════════════════════════════════════
# TEST 3: Shorter replacement (delta < 0)
# ══════════════════════════════════════════════════════════
Write-Host "`n── TEST 3: Shorter replacement (delta < 0) ──" -ForegroundColor Cyan
$text3 = 'هذا النصص خاطئ والكلمه خطأ'
$sugs3 = @(
    @{ id='x'; start=4; end=9; original='النصص'; correction='النص'; type='spelling' },
    @{ id='y'; start=17; end=23; original='والكلمه'; correction='والكلمة'; type='spelling' }
)
$result = ApplyAndRebase $text3 $sugs3[0] 'النص' $sugs3
Assert-Equal $result.text 'هذا النص خاطئ والكلمه خطأ' 'Text: النصص → النص'
Assert-True ($result.suggestions.Count -eq 1) '1 remaining'
Assert-Equal $result.suggestions[0].start 16 'Suggestion Y start shifted 17→16 (-1)'
Assert-Equal $result.suggestions[0].end 22 'Suggestion Y end shifted 23→22 (-1)'
$extracted = $result.text.Substring($result.suggestions[0].start, $result.suggestions[0].end - $result.suggestions[0].start)
Assert-Equal $extracted 'والكلمه' 'Rebased offset Y extracts correct text'

# ══════════════════════════════════════════════════════════
# TEST 4: Multiple sequential applies
# ══════════════════════════════════════════════════════════
Write-Host "`n── TEST 4: Multiple sequential applies ──" -ForegroundColor Cyan
$text4 = $TEXT
$sugs4 = MakeSuggestions
$r1 = ApplyAndRebase $text4 $sugs4[0] 'إلى' $sugs4
$text4 = $r1.text; $sugs4 = $r1.suggestions
Assert-Equal $text4 'أنا ذاهب إلى البت والمدرسه' 'After apply A'
Assert-True ($sugs4.Count -eq 2) '2 remaining after A'

$r2 = ApplyAndRebase $text4 $sugs4[0] 'البيت' $sugs4
$text4 = $r2.text; $sugs4 = $r2.suggestions
Assert-Equal $text4 'أنا ذاهب إلى البيت والمدرسه' 'After apply B'
Assert-True ($sugs4.Count -eq 1) '1 remaining after B'

$r3 = ApplyAndRebase $text4 $sugs4[0] 'المدرسة' $sugs4
$text4 = $r3.text; $sugs4 = $r3.suggestions
Assert-Equal $text4 'أنا ذاهب إلى البيت والمدرسة' 'After apply C — fully corrected'
Assert-True ($sugs4.Count -eq 0) '0 remaining — all applied'

$expectedFull = ApplyAllPatches $TEXT (MakeSuggestions)
Assert-Equal $text4 $expectedFull 'Sequential === applyAllPatches'

# ══════════════════════════════════════════════════════════
# TEST 5: Apply last suggestion
# ══════════════════════════════════════════════════════════
Write-Host "`n── TEST 5: Apply last suggestion ──" -ForegroundColor Cyan
$sugs5 = MakeSuggestions
$result = ApplyAndRebase $TEXT $sugs5[2] 'المدرسة' $sugs5
Assert-Equal $result.text 'أنا ذاهب الى البت والمدرسة' 'Last suggestion applied'
Assert-True ($result.suggestions.Count -eq 2) '2 remaining'
Assert-Equal $result.suggestions[0].start 10 'A unchanged (before C)'
Assert-Equal $result.suggestions[1].start 14 'B unchanged (before C)'

# ══════════════════════════════════════════════════════════
# TEST 6: applyAllPatches
# ══════════════════════════════════════════════════════════
Write-Host "`n── TEST 6: applyAllPatches ──" -ForegroundColor Cyan
$resultAll = ApplyAllPatches $TEXT (MakeSuggestions)
Assert-Equal $resultAll 'أنا ذاهب إلى البيت والمدرسة' 'All patches applied correctly'

# ══════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════
Write-Host "`n$('═' * 50)"
if ($failed -gt 0) {
    Write-Host "Results: $passed passed, $failed FAILED" -ForegroundColor Red
    exit 1
} else {
    Write-Host "Results: $passed passed, $failed failed" -ForegroundColor Green
    exit 0
}
