Add-Type -AssemblyName System.Drawing

try {
    $img = [System.Drawing.Image]::FromFile('d:\mathagentdevelop\agent要求.png')
    Write-Host "Width: $($img.Width) x Height: $($img.Height)"
    Write-Host "PixelFormat: $($img.PixelFormat)"

    # Check for property items (metadata - might contain text)
    foreach($prop in $img.PropertyItems) {
        Write-Host "Property ID: $($prop.Id), Type: $($prop.Type), Len: $($prop.Len)"
        $text = [System.Text.Encoding]::UTF8.GetString($prop.Value)
        Write-Host "Value: $text"
    }

    $img.Dispose()
    Write-Host "Done reading metadata."
} catch {
    Write-Host "Error: $($_.Exception.Message)"
}
