param(
    [Parameter(Mandatory = $true)]
    [string]$LogPath,

    [Parameter(Mandatory = $false)]
    [string]$Title = "Stellar Blade FBX Export Log"
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Windows.Forms, System.Drawing -TypeDefinition @'
using System;
using System.Drawing;
using System.Windows.Forms;
using System.Runtime.InteropServices;
public sealed class StellarBladeLogTextBox : RichTextBox {
    public StellarBladeLogScrollBar LogScrollBar { get; set; }
    protected override void WndProc(ref Message message) {
        // RichEdit does not reliably scroll with its native scrollbars disabled.
        if (message.Msg == 0x020A && LogScrollBar != null) {
            LogScrollBar.ScrollWheel((short)((message.WParam.ToInt64() >> 16) & 0xffff));
            message.Result = IntPtr.Zero;
            return;
        }
        base.WndProc(ref message);
    }
}
// Paint the entire scrollbar ourselves: native RichEdit scrollbars can ignore
// Windows' dark theme, particularly when hosted by Windows PowerShell.
public sealed class StellarBladeLogScrollBar : Control {
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    private static extern IntPtr SendMessage(IntPtr window, int message, IntPtr wParam, IntPtr lParam);
    private readonly RichTextBox editor;
    private bool dragging;
    private bool hovering;
    private int dragOffset;
    private int wheelRemainder;

    public StellarBladeLogScrollBar(RichTextBox editor) {
        this.editor = editor;
        SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint |
                 ControlStyles.OptimizedDoubleBuffer | ControlStyles.ResizeRedraw, true);
        BackColor = Color.FromArgb(36, 36, 36);
        Width = 14;
        Dock = DockStyle.Right;
        TabStop = false;
        AccessibleName = "Export log scrollbar";
        AccessibleRole = AccessibleRole.ScrollBar;
        editor.VScroll += delegate { Invalidate(); };
        editor.TextChanged += delegate { Invalidate(); };
        editor.Resize += delegate { Invalidate(); };
    }

    public int FirstLine {
        get { return (int)SendMessage(editor.Handle, 0x00CE, IntPtr.Zero, IntPtr.Zero); }
    }
    private int LineCount { get { return editor.GetLineFromCharIndex(editor.TextLength) + 1; } }
    private int PageLines { get { return Math.Max(1, editor.ClientSize.Height / editor.Font.Height); } }
    public int Maximum { get { return Math.Max(0, LineCount - PageLines); } }
    public Rectangle ThumbBounds {
        get {
            int height = Math.Min(Height, Math.Max(28, (int)((long)Height * PageLines / LineCount)));
            int top = Maximum == 0 ? 0 : (int)((long)(Height - height) * Math.Min(FirstLine, Maximum) / Maximum);
            return new Rectangle(3, top, Math.Max(1, Width - 6), height);
        }
    }
    public void ScrollToLine(int line) {
        int target = Math.Max(0, Math.Min(Maximum, line));
        SendMessage(editor.Handle, 0x00B6, IntPtr.Zero, new IntPtr(target - FirstLine));
        Invalidate();
    }
    protected override void OnPaint(PaintEventArgs e) {
        e.Graphics.Clear(BackColor);
        if (Maximum == 0) return;
        using (var brush = new SolidBrush(hovering || dragging ? Color.FromArgb(112, 112, 112) : Color.FromArgb(84, 84, 84))) {
            e.Graphics.FillRectangle(brush, ThumbBounds);
        }
    }
    protected override void OnMouseDown(MouseEventArgs e) {
        base.OnMouseDown(e);
        if (e.Button != MouseButtons.Left || Maximum == 0) return;
        Rectangle thumb = ThumbBounds;
        if (e.Y >= thumb.Top && e.Y < thumb.Bottom) {
            dragging = true;
            dragOffset = e.Y - thumb.Top;
            Capture = true;
        } else {
            ScrollToLine(FirstLine + (e.Y < thumb.Top ? -PageLines : PageLines));
        }
        Invalidate();
    }
    protected override void OnMouseMove(MouseEventArgs e) {
        base.OnMouseMove(e);
        if (dragging) {
            int travel = Math.Max(1, Height - ThumbBounds.Height);
            int position = Math.Max(0, Math.Min(travel, e.Y - dragOffset));
            ScrollToLine((int)((long)position * Maximum / travel));
        }
    }
    protected override void OnMouseUp(MouseEventArgs e) {
        base.OnMouseUp(e);
        if (e.Button == MouseButtons.Left) { dragging = false; Capture = false; Invalidate(); }
    }
    protected override void OnMouseCaptureChanged(EventArgs e) {
        base.OnMouseCaptureChanged(e);
        if (!Capture) { dragging = false; Invalidate(); }
    }
    protected override void OnMouseEnter(EventArgs e) { base.OnMouseEnter(e); hovering = true; Invalidate(); }
    protected override void OnMouseLeave(EventArgs e) { base.OnMouseLeave(e); hovering = false; Invalidate(); }
    protected override void OnMouseWheel(MouseEventArgs e) {
        base.OnMouseWheel(e);
        ScrollWheel(e.Delta);
    }
    public void ScrollWheel(int delta) {
        wheelRemainder += delta;
        int steps = wheelRemainder / 120;
        wheelRemainder %= 120;
        int lines = SystemInformation.MouseWheelScrollLines;
        ScrollToLine(FirstLine - steps * (lines < 0 ? PageLines : lines));
    }
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

$textBox = New-Object StellarBladeLogTextBox
$textBox.Multiline = $true
$textBox.ReadOnly = $true
$textBox.ScrollBars = 'None'
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
$scrollBar = New-Object StellarBladeLogScrollBar($textBox)
$textBox.LogScrollBar = $scrollBar
$logPanel.Controls.Add($scrollBar)

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
$copyButton = New-Object System.Windows.Forms.Button
$copyButton.Text = 'Copy Log'
$copyButton.Size = $closeButton.Size
$copyButton.Top = $closeButton.Top
$copyButton.Left = $closeButton.Left - $copyButton.Width - 8
$copyButton.Anchor = 'Top,Right'
$copyButton.FlatStyle = 'Flat'
$copyButton.FlatAppearance.BorderSize = 0
$copyButton.BackColor = $buttonColor
$copyButton.ForeColor = $form.ForeColor
$copyButton.FlatAppearance.MouseOverBackColor = $closeButton.FlatAppearance.MouseOverBackColor
$copyResetTimer = New-Object System.Windows.Forms.Timer
$copyResetTimer.Interval = 2000
$copyResetTimer.Add_Tick({
    $copyResetTimer.Stop()
    $copyButton.Text = 'Copy Log'
})
$copyButton.Add_Click({
    try {
        # Include data written since the last timer tick, and copy the entire log.
        if (Test-Path -LiteralPath $LogPath) {
            Update-LogContents ([System.IO.File]::ReadAllText($LogPath))
        }
        if ($textBox.TextLength -gt 0) {
            [System.Windows.Forms.Clipboard]::SetText($textBox.Text)
            $copyButton.Text = 'Copied'
            $copyResetTimer.Stop()
            $copyResetTimer.Start()
        }
    } catch {
        [void][System.Windows.Forms.MessageBox]::Show($form, 'Could not copy the log. Please try again.', 'Copy Log')
    }
})
$buttonPanel.Controls.Add($copyButton)
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
    $copyButton.Left = $closeButton.Left - $copyButton.Width - 8
    $grip.Left = $buttonPanel.Width - 24
    $grip.Top = $buttonPanel.Height - 24
})

function Update-LogContents([string]$content) {
    $content = $content.Replace("`r`n", "`n")
    if ($content -ceq $script:lastText) { return }
    $firstLine = $scrollBar.FirstLine
    $followEnd = $firstLine -ge ($scrollBar.Maximum - 1)
    $selectionStart = $textBox.SelectionStart
    $selectionLength = $textBox.SelectionLength
    if ($content.StartsWith($script:lastText, [System.StringComparison]::Ordinal)) {
        $textBox.AppendText($content.Substring($script:lastText.Length))
    } else {
        $textBox.Text = $content
    }
    $script:lastText = $content
    $textBox.Select([Math]::Min($selectionStart, $textBox.TextLength),
        [Math]::Min($selectionLength, [Math]::Max(0, $textBox.TextLength - $selectionStart)))
    if ($followEnd) { $scrollBar.ScrollToLine($scrollBar.Maximum) }
    else { $scrollBar.ScrollToLine($firstLine) }
}

$script:lastText = ""
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 100
$timer.Add_Tick({
    $scrollBar.Invalidate()
    if (Test-Path -LiteralPath $LogPath) {
        try {
            Update-LogContents ([System.IO.File]::ReadAllText($LogPath))
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
    $copyResetTimer.Stop()
    $copyResetTimer.Dispose()
    $timer.Stop()
    $timer.Dispose()
})

[void]$form.ShowDialog()
$form.Dispose()
