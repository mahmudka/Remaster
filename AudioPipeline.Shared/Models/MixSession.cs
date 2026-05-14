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

    public float? Bpm { get; set; }

    [MaxLength(50)]
    public string? Key { get; set; }

    public string? MixPlanJson { get; set; }

    [MaxLength(50)]
    public string Status { get; set; } = "Pending";

    [MaxLength(500)]
    public string? BlocksRun { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? CompletedAt { get; set; }

    public TrackDiagnosis? Diagnosis { get; set; }
    public ICollection<ProcessingIteration> Iterations { get; set; } = new List<ProcessingIteration>();
    public ICollection<SimilarityReport> SimilarityReports { get; set; } = new List<SimilarityReport>();
    public ICollection<UserFeedback> Feedbacks { get; set; } = new List<UserFeedback>();
}
