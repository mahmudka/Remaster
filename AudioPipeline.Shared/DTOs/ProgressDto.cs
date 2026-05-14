namespace AudioPipeline.Shared.DTOs;

public class ProgressDto
{
    public string JobId { get; set; } = string.Empty;
    public string Block { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;  // "running" | "done" | "error"
    public string Message { get; set; } = string.Empty;
    public int ProgressPercent { get; set; }
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
}
