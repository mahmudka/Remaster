using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AudioPipeline.Shared.Models;

[Table("SimilarityReports")]
public class SimilarityReport
{
    [Key]
    public int Id { get; set; }

    public int SessionId { get; set; }
    public int? IterationId { get; set; }
    public double? SimilarityScore { get; set; }
    public string? FrequencyDiffJson { get; set; }
    public string? DynamicsDiffJson { get; set; }
    public string? ReportJson { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [ForeignKey(nameof(SessionId))]
    public MixSession Session { get; set; } = null!;

    [ForeignKey(nameof(IterationId))]
    public ProcessingIteration? Iteration { get; set; }
}
