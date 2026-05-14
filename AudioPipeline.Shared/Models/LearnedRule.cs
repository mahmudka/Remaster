using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AudioPipeline.Shared.Models;

[Table("LearnedRules")]
public class LearnedRule
{
    [Key]
    public int Id { get; set; }

    [Required, MaxLength(100)]
    public string Genre { get; set; } = string.Empty;

    [Required, MaxLength(200)]
    public string Parameter { get; set; } = string.Empty;

    [Required, MaxLength(500)]
    public string Value { get; set; } = string.Empty;

    [MaxLength(50)]
    public string? Unit { get; set; }

    public double Confidence { get; set; } = 0.5;
    public int SampleCount { get; set; } = 0;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}
