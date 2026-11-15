param([string]$in, [string]$out)
$w = New-Object -ComObject Word.Application
$w.Visible = $false; $w.DisplayAlerts = 0
$doc = $w.Documents.Open($in, $false, $true)
$doc.Fields.Update() | Out-Null
$doc.ExportAsFixedFormat($out, 17)
$doc.Close(0); $w.Quit()
"pdf ok"
