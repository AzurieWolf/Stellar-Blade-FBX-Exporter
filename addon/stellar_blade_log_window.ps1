param(
    [Parameter(Mandatory = $true)]
    [string]$LogPath,

    [Parameter(Mandatory = $false)]
    [string]$Title = "Stellar Blade FBX Export Log"
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = $Title
$form.Width = 900
$form.Height = 520
$form.StartPosition = "CenterScreen"

$textBox = New-Object System.Windows.Forms.TextBox
$textBox.Multiline = $true
$textBox.ReadOnly = $true
$textBox.ScrollBars = "Both"
$textBox.WordWrap = $false
$textBox.Font = New-Object System.Drawing.Font("Consolas", 9)
$textBox.Dock = "Fill"

$buttonPanel = New-Object System.Windows.Forms.Panel
$buttonPanel.Height = 42
$buttonPanel.Dock = "Bottom"

$closeButton = New-Object System.Windows.Forms.Button
$closeButton.Text = "Close"
$closeButton.Width = 90
$closeButton.Height = 26
$closeButton.Anchor = "Top,Right"
$closeButton.Left = $buttonPanel.Width - $closeButton.Width - 8
$closeButton.Top = 8
$closeButton.Add_Click({ $form.Close() })

$buttonPanel.Controls.Add($closeButton)
$form.Controls.Add($textBox)
$form.Controls.Add($buttonPanel)

$buttonPanel.Add_Resize({
    $closeButton.Left = $buttonPanel.Width - $closeButton.Width - 8
})

$lastText = ""
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 100
$timer.Add_Tick({
    if (Test-Path -LiteralPath $LogPath) {
        try {
            $text = [System.IO.File]::ReadAllText($LogPath)
            if ($text -ne $lastText) {
                $script:lastText = $text
                $textBox.Text = $text
                $textBox.SelectionStart = $textBox.TextLength
                $textBox.ScrollToCaret()
            }
        }
        catch {
        }
    }
})

$form.Add_Shown({
    $timer.Start()
    $form.Activate()
})

$form.Add_FormClosed({
    $timer.Stop()
    $timer.Dispose()
})

[void]$form.ShowDialog()
