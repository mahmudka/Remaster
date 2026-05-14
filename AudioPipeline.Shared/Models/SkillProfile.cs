using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AudioPipeline.Shared.Models;

[Table("SkillProfiles")]
public class SkillProfile
{
    [Key]
    public int Id { get; set; }

    [Required, MaxLength(100)]
    public string Genre { get; set; } = string.Empty;

    [MaxLength(200)]
    public string? ProfileName { get; set; }

    public string? ParametersJson { get; set; }
    public int SessionCount { get; set; } = 0;
    public double? AvgRating { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
}
