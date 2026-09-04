param(
    [string]$PackageVersion = "0.14.0-dev"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$EditionFile = Join-Path $ProjectRoot "app\edition.py"
$SpecFile = Join-Path $ProjectRoot "AlbumCropStudio.spec"
$EnglishTs = Join-Path $ProjectRoot "translations\albumcrop_en.ts"
$EnglishQm = Join-Path $ProjectRoot "translations\albumcrop_en.qm"
$ChineseTs = Join-Path $ProjectRoot "translations\albumcrop_zh_TW.ts"
$ChineseQm = Join-Path $ProjectRoot "translations\albumcrop_zh_TW.qm"
$DistDir = Join-Path $ProjectRoot "dist\AlbumCropStudio"
$PackageDir = Join-Path $ProjectRoot "packages"
$ZipName = "AlbumCropStudio-$PackageVersion-internal-win-x64.zip"
$ZipPath = Join-Path $PackageDir $ZipName

Write-Host ""
Write-Host "==============================================="
Write-Host " AlbumCrop Studio Internal Build"
Write-Host "==============================================="
Write-Host ""
Write-Host "Package version : $PackageVersion"
Write-Host "Output          : $ZipPath"
Write-Host ""

if (-not (Test-Path $EditionFile)) {
    throw "app\edition.py が見つかりません。"
}

if (-not (Test-Path $SpecFile)) {
    throw "AlbumCropStudio.spec が見つかりません。"
}

$OriginalEditionContent = Get-Content `
    -Path $EditionFile `
    -Raw `
    -Encoding UTF8

try {
    Write-Host "[1/7] Internal版へ一時切り替え..."

    $InternalEditionContent = $OriginalEditionContent -replace `
        'CURRENT_EDITION\s*=\s*EDITION_FREE', `
        'CURRENT_EDITION = EDITION_INTERNAL'

    if ($InternalEditionContent -eq $OriginalEditionContent) {
        if (
            $OriginalEditionContent -notmatch
            'CURRENT_EDITION\s*=\s*EDITION_INTERNAL'
        ) {
            throw "CURRENT_EDITION の定義を見つけられませんでした。"
        }
    }
    else {
        Set-Content `
            -Path $EditionFile `
            -Value $InternalEditionContent `
            -Encoding UTF8
    }

    Write-Host "[2/7] edition.py 構文確認..."
    python -m py_compile app\edition.py

    Write-Host "[3/7] 英語翻訳を生成..."
    pyside6-lrelease `
        $EnglishTs `
        -qm $EnglishQm

    Write-Host "[4/7] 繁體中文翻訳を生成..."
    pyside6-lrelease `
        $ChineseTs `
        -qm $ChineseQm

    Write-Host "[5/7] PyInstallerビルド..."
    pyinstaller `
        --noconfirm `
        $SpecFile

    if (-not (Test-Path $DistDir)) {
        throw "dist\AlbumCropStudio が生成されませんでした。"
    }

    Write-Host "[6/7] 配布用ZIPを作成..."

    New-Item `
        -ItemType Directory `
        -Force `
        -Path $PackageDir `
        | Out-Null

    if (Test-Path $ZipPath) {
        Remove-Item `
            -Path $ZipPath `
            -Force
    }

    Compress-Archive `
        -Path (Join-Path $DistDir "*") `
        -DestinationPath $ZipPath `
        -CompressionLevel Optimal

    if (-not (Test-Path $ZipPath)) {
        throw "ZIPファイルを作成できませんでした。"
    }

    Write-Host "[7/7] 完了"
    Write-Host ""
    Write-Host "Internal版ZIPを作成しました:"
    Write-Host $ZipPath
    Write-Host ""
}
finally {
    Write-Host ""
    Write-Host "Free版へ復帰しています..."

    Set-Content `
        -Path $EditionFile `
        -Value $OriginalEditionContent `
        -Encoding UTF8

    try {
        python -m py_compile app\edition.py
        Write-Host "元のFree版設定へ復帰しました。"
    }
    catch {
        Write-Warning "edition.py の復帰後構文確認に失敗しました。"
        throw
    }
}

Write-Host ""
Write-Host "==============================================="
Write-Host " Build finished"
Write-Host "==============================================="
Write-Host ""
