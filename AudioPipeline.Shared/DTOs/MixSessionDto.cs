namespace AudioPipeline.Shared.DTOs;

public class MixSessionDto
{
    public int Id { get; set; }
    public string JobId { get; set; } = string.Empty;
    public string InputFile { get; set; } = string.Empty;
    public string? Genre { get; set; }
    public float? Bpm { get; set; }
    public string? Key { get; set; }
    public string Status { get; set; } = string.Empty;
    public string? BlocksRun { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? CompletedAt { get; set; }
    public int? UserRating { get; set; }
}

public class CreateMixSessionDto
{
    public string InputFile { get; set; } = string.Empty;
    public string? OutputPath { get; set; }
    public string? ReferenceFile { get; set; }
    public string? RvcModelPath { get; set; }
    public List<string> SelectedBlocks { get; set; } = new();
}
