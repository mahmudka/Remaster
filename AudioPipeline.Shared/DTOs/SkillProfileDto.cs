namespace AudioPipeline.Shared.DTOs;

public class SkillProfileDto
{
    public int Id { get; set; }
    public string Genre { get; set; } = string.Empty;
    public string? ProfileName { get; set; }
    public int SessionCount { get; set; }
    public double? AvgRating { get; set; }
    public DateTime UpdatedAt { get; set; }
    public Dictionary<string, object>? Parameters { get; set; }
}
