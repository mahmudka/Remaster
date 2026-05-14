using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AudioPipeline.Shared.Models;

[Table("UserFeedback")]
public class UserFeedback
{
    [Key]
    public int Id { get; set; }

    public int SessionId { get; set; }

    [Range(1, 5)]
    public int Rating { get; set; }

    [MaxLength(500)]
    public string? FeedbackTagsJson { get; set; }

    public string? UserNote { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [ForeignKey(nameof(SessionId))]
    public MixSession Session { get; set; } = null!;
}
