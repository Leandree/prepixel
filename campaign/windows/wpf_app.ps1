# Throwaway WPF probe app (real PresentationFramework stack, no SDK needed).
# TextBox (T1/T3), Button incrementing a counter (T5 in-channel verify),
# unlabeled Image (T6 pictorial), all with AutomationIds.
Add-Type -AssemblyName PresentationFramework
$xaml = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="pipeline-tap WPF probe" Width="560" Height="420"
        Left="200" Top="150">
  <StackPanel Margin="16">
    <TextBlock Text="WPF-TAP-SENTINEL café naïve 日本語 END" FontSize="16"/>
    <TextBox x:Name="Field" AutomationProperties.AutomationId="Field"
             Text="initial" Margin="0,12,0,0" Width="300" HorizontalAlignment="Left"/>
    <StackPanel Orientation="Horizontal" Margin="0,12,0,0">
      <Button x:Name="Bump" AutomationProperties.AutomationId="Bump"
              Content="Increment" Width="110"/>
      <TextBlock x:Name="Counter" AutomationProperties.AutomationId="Counter"
                 Text="count=0" Margin="12,4,0,0"/>
    </StackPanel>
    <CheckBox x:Name="Chk" Content="Option armée" Margin="0,12,0,0"/>
    <Border Width="220" Height="120" Margin="0,16,0,0" HorizontalAlignment="Left"
            Background="Black">
      <Canvas x:Name="Cnv">
        <TextBlock Canvas.Left="30" Canvas.Top="45" Foreground="White"
                   FontSize="18" Text="painted-in-canvas"/>
      </Canvas>
    </Border>
  </StackPanel>
</Window>
'@
$win = [Windows.Markup.XamlReader]::Parse($xaml)
$count = 0
$btn = $win.FindName('Bump')
$cnt = $win.FindName('Counter')
$btn.Add_Click({ $script:count++; $cnt.Text = "count=$script:count" })
$null = $win.ShowDialog()
