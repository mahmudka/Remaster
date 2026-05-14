using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AudioPipeline.Shared.Models;

[Table("ProcessingIterations")]
public class ProcessingIteration
{
    [Key]
    public int Id { get; set; }

    public int SessionId { get; set; }

    [Required, MaxLength(50)]
    public string IterationType { get; set; } = string.Empty;  // "mix" | "master"

    public int IterationNumber { get; set; }
    public string? ParametersJson { get; set; }

    [MaxLength(1000)]
    public string? OutputFile { get; set; }

    public double? LufsIntegrated { get; set; }
    public double? LufsTruePeak { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [ForeignKey(nameof(SessionId))]
    public MixSession Session { get; set; } = null!;
}
