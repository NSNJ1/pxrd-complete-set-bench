param(
    [int]$Parts = 16,
    [int]$Concurrency = 2,
    [string]$Url = "https://zenodo.org/api/records/21285546/files/refinement_pkls.zip/content",
    [long]$TotalBytes = 291408941,
    [string]$ExpectedMd5 = "49447823b4e017524fd963ec3734af74"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$output = Join-Path $root "refinement_pkls.zip"
$rangeDir = Join-Path $root "refinement_pkls_ranges"
New-Item -ItemType Directory -Path $rangeDir -Force | Out-Null

$chunkSize = [long][Math]::Ceiling($TotalBytes / $Parts)
$pending = @()
for ($index = 0; $index -lt $Parts; $index++) {
    $start = [long]$index * $chunkSize
    $end = [Math]::Min($TotalBytes - 1, $start + $chunkSize - 1)
    $expectedLength = $end - $start + 1
    $chunkPath = Join-Path $rangeDir ("part_{0:D2}.bin" -f $index)
    if (
        (Test-Path -LiteralPath $chunkPath) -and
        ((Get-Item -LiteralPath $chunkPath).Length -eq $expectedLength)
    ) {
        continue
    }
    $pending += [pscustomobject]@{
        Index = $index
        Range = "$start-$end"
        Path = $chunkPath
        Length = $expectedLength
    }
}

for ($offset = 0; $offset -lt $pending.Count; $offset += $Concurrency) {
    $endIndex = [Math]::Min($offset + $Concurrency - 1, $pending.Count - 1)
    $batch = @($pending[$offset..$endIndex])
    $jobs = @()
    foreach ($item in $batch) {
        Write-Host ("starting part {0}: {1}" -f $item.Index, $item.Range)
        $jobs += Start-Job -ScriptBlock {
            param($CurlUrl, $Range, $Destination, $ExpectedLength)
            $ErrorActionPreference = "Stop"
            & curl.exe `
                --silent `
                --show-error `
                --location `
                --fail `
                --retry 12 `
                --retry-all-errors `
                --retry-delay 5 `
                --connect-timeout 30 `
                --max-time 1800 `
                --range $Range `
                --output $Destination `
                $CurlUrl
            if ($LASTEXITCODE -ne 0) {
                throw "curl failed for $Range with exit code $LASTEXITCODE"
            }
            $observedLength = (Get-Item -LiteralPath $Destination).Length
            if ($observedLength -ne $ExpectedLength) {
                throw "range $Range has $observedLength bytes; expected $ExpectedLength"
            }
        } -ArgumentList $Url, $item.Range, $item.Path, $item.Length
    }

    while (($jobs | Where-Object State -eq "Running").Count -gt 0) {
        Start-Sleep -Seconds 3
    }
    foreach ($job in $jobs) {
        Receive-Job -Job $job -Wait -AutoRemoveJob -ErrorAction Stop
    }
}

$partial = "$output.partial"
$stream = [System.IO.File]::Open(
    $partial,
    [System.IO.FileMode]::Create,
    [System.IO.FileAccess]::Write,
    [System.IO.FileShare]::None
)
try {
    for ($index = 0; $index -lt $Parts; $index++) {
        $chunk = Join-Path $rangeDir ("part_{0:D2}.bin" -f $index)
        $input = [System.IO.File]::OpenRead($chunk)
        try {
            $input.CopyTo($stream)
        }
        finally {
            $input.Dispose()
        }
    }
}
finally {
    $stream.Dispose()
}

$observedBytes = (Get-Item -LiteralPath $partial).Length
if ($observedBytes -ne $TotalBytes) {
    throw "assembled file has $observedBytes bytes; expected $TotalBytes"
}
$observedMd5 = (Get-FileHash -Algorithm MD5 -LiteralPath $partial).Hash.ToLowerInvariant()
if ($observedMd5 -ne $ExpectedMd5.ToLowerInvariant()) {
    throw "MD5 mismatch: $observedMd5"
}
Move-Item -LiteralPath $partial -Destination $output -Force
Write-Host "verified refinement pkls: $output"
Write-Host "bytes: $observedBytes"
Write-Host "md5: $observedMd5"
