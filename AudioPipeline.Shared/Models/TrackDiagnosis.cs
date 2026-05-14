using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AudioPipeline.Shared.Models;

[Table("TrackDiagnosis")]
public class TrackDiagnosis
{
    [Key]
    public int Id { get; set; }

    public int SessionId { get; set; }
    public string? FrequencyMapJson { get; set; }
    public string? DynamicsProfileJson { get; set; }
    public string? StereoProfileJson { get; set; }
    public string? ProblemsJson { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [ForeignKey(nameof(SessionId))]
    public MixSession Session { get; set; } = null!;
}
