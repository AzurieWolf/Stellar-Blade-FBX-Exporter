param(
    [Parameter(Mandatory = $true)]
    [string]$LogPath,

    [Parameter(Mandatory = $false)]
    [string]$Title = "Stellar Blade FBX Export Log"
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class StellarBladeLogTheme {
    [DllImport("uxtheme.dll", CharSet = CharSet.Unicode)]
    public static extern int SetWindowTheme(IntPtr window, string appName, string idList);
}
'@

$form = New-Object System.Windows.Forms.Form
$form.Text = $Title
$form.Width = 900
$form.Height = 520
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "None"
$form.ControlBox = $false
$form.MinimizeBox = $false
$form.MaximizeBox = $false
$form.MinimumSize = New-Object System.Drawing.Size(480, 280)
$form.BackColor = [System.Drawing.ColorTranslator]::FromHtml('#484848')
$form.ForeColor = [System.Drawing.ColorTranslator]::FromHtml('#d4d4d4')
$form.Padding = New-Object System.Windows.Forms.Padding(1)
$form.Font = New-Object System.Drawing.Font('Segoe UI', 10)

$background = [System.Drawing.ColorTranslator]::FromHtml('#303030')
$field = [System.Drawing.ColorTranslator]::FromHtml('#242424')
$buttonColor = [System.Drawing.ColorTranslator]::FromHtml('#545454')

# A custom title bar keeps the palette independent of Windows' light/dark mode.
$titleBar = New-Object System.Windows.Forms.Label
$titleBar.Text = $Title
$titleBar.Dock = 'Top'
$titleBar.Height = 38
$titleBar.TextAlign = 'MiddleLeft'
$titleBar.Padding = New-Object System.Windows.Forms.Padding(12, 0, 0, 0)
$titleBar.BackColor = $background
$titleBar.Add_MouseDown({
    if ($_.Button -eq [System.Windows.Forms.MouseButtons]::Left) {
        $script:dragStart = [System.Windows.Forms.Cursor]::Position
        $script:formStart = $form.Location
        $titleBar.Capture = $true
    }
})
$titleBar.Add_MouseMove({
    if ($titleBar.Capture -and $_.Button -eq [System.Windows.Forms.MouseButtons]::Left) {
        $point = [System.Windows.Forms.Cursor]::Position
        $form.Location = New-Object System.Drawing.Point(
            ($script:formStart.X + $point.X - $script:dragStart.X),
            ($script:formStart.Y + $point.Y - $script:dragStart.Y))
    }
})
$titleBar.Add_MouseUp({ $titleBar.Capture = $false })

$textBox = New-Object System.Windows.Forms.RichTextBox
$textBox.Multiline = $true
$textBox.ReadOnly = $true
$textBox.ScrollBars = 'Vertical'
$textBox.WordWrap = $true
$textBox.DetectUrls = $false
$textBox.BorderStyle = 'None'
$textBox.BackColor = $field
$textBox.ForeColor = $form.ForeColor
$textBox.Font = New-Object System.Drawing.Font("Consolas", 10)
$textBox.Dock = "Fill"

$logPanel = New-Object System.Windows.Forms.Panel
$logPanel.Dock = 'Fill'
$logPanel.BackColor = $field
$logPanel.Padding = New-Object System.Windows.Forms.Padding(10, 8, 8, 8)
$logPanel.Controls.Add($textBox)

$bodyPanel = New-Object System.Windows.Forms.Panel
$bodyPanel.Dock = 'Fill'
$bodyPanel.BackColor = $background
$bodyPanel.Padding = New-Object System.Windows.Forms.Padding(8, 0, 8, 0)
$bodyPanel.Controls.Add($logPanel)

$buttonPanel = New-Object System.Windows.Forms.Panel
$buttonPanel.Height = 46
$buttonPanel.Dock = "Bottom"
$buttonPanel.BackColor = $background

$closeButton = New-Object System.Windows.Forms.Button
$closeButton.Text = "Close"
$closeButton.Width = 90
$closeButton.Height = 30
$closeButton.FlatStyle = 'Flat'
$closeButton.FlatAppearance.BorderSize = 0
$closeButton.BackColor = $buttonColor
$closeButton.ForeColor = $form.ForeColor
$closeButton.FlatAppearance.MouseOverBackColor = [System.Drawing.ColorTranslator]::FromHtml('#646464')
$closeButton.Anchor = "Top,Right"
$closeButton.Left = $buttonPanel.Width - $closeButton.Width - 30
$closeButton.Top = 8
$closeButton.Add_Click({ $form.Close() })

$buttonPanel.Controls.Add($closeButton)
$grip = New-Object System.Windows.Forms.Label
$grip.Text = [char]0x25E2
$grip.ForeColor = [System.Drawing.ColorTranslator]::FromHtml('#777777')
$grip.Size = New-Object System.Drawing.Size(20, 20)
$grip.Cursor = [System.Windows.Forms.Cursors]::SizeNWSE
$grip.Anchor = 'Bottom,Right'
$grip.Add_MouseDown({
    if ($_.Button -eq [System.Windows.Forms.MouseButtons]::Left) {
        $script:resizeStart = [System.Windows.Forms.Cursor]::Position
        $script:sizeStart = $form.Size
        $grip.Capture = $true
    }
})
$grip.Add_MouseMove({
    if ($grip.Capture -and $_.Button -eq [System.Windows.Forms.MouseButtons]::Left) {
        $point = [System.Windows.Forms.Cursor]::Position
        $form.Size = New-Object System.Drawing.Size(
            ([Math]::Max(480, $script:sizeStart.Width + $point.X - $script:resizeStart.X)),
            ([Math]::Max(280, $script:sizeStart.Height + $point.Y - $script:resizeStart.Y)))
    }
})
$grip.Add_MouseUp({ $grip.Capture = $false })
$buttonPanel.Controls.Add($grip)
$form.Controls.Add($bodyPanel)
$form.Controls.Add($buttonPanel)
$form.Controls.Add($titleBar)

$buttonPanel.Add_Resize({
    $closeButton.Left = $buttonPanel.Width - $closeButton.Width - 30
    $grip.Left = $buttonPanel.Width - 24
    $grip.Top = $buttonPanel.Height - 24
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
    # Dark scrollbar on Windows versions that support the Explorer dark theme.
    [void][StellarBladeLogTheme]::SetWindowTheme($textBox.Handle, 'DarkMode_Explorer', $null)
    $timer.Start()
    $form.Activate()
})

$form.Add_FormClosed({
    $timer.Stop()
    $timer.Dispose()
})

[void]$form.ShowDialog()
$form.Dispose()
