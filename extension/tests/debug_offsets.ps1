$t = 'أنا ذاهب الى البت والمدرسه'
Write-Host "Length: $($t.Length)"
Write-Host "Chars 10-13: '$($t.Substring(10, 3))'"
Write-Host "Chars 14-17: '$($t.Substring(14, 3))'"
Write-Host "Chars 19-26: '$($t.Substring(19, 7))'"

# Direct test: substring replacement
$before = $t.Substring(0, 10)
$after = $t.Substring(13)
$result = $before + 'إلى' + $after
Write-Host "`nReplace [10:13] 'الى' with 'إلى':"
Write-Host "Result: '$result'"
Write-Host "Expected: 'أنا ذاهب إلى البت والمدرسه'"
Write-Host "Match: $($result -eq 'أنا ذاهب إلى البت والمدرسه')"
