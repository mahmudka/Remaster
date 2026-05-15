using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AudioPipeline.Shared.Models;

[Table("MixSessions")]
public class MixSession
{
    [Key]
    public int Id { get; set; }

    [Required, MaxLength(100)]
    public string JobId { get; set; } = string.Empty;

    [Required, MaxLength(1000)]
    public string InputFile { get; set; } = string.Empty;

    [MaxLength(1000)]
    public string? OutputPath { get; set; }

    [MaxLength(100)]
    public string? Genre { get; set; }

    public double? Bpm { get; set; }

    [MaxLength(50)]
    public string? Key { get; set; }

    [MaxLength(50)]
    public string Status { get; set; } = "Pending";

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? CompletedAt { get; set; }

    // v2 fields
    public string? AnalysisBeforeJson  { get; set; }
    public string? AnalysisAfterJson   { get; set; }
    public string? PlanJson            { get; set; }

    [MaxLength(1000)]
    public string? ProblemsDetected    { get; set; }

    public ICollection<UserFeedback> Feedbacks { get; set; } = new List<UserFeedback>();
}
