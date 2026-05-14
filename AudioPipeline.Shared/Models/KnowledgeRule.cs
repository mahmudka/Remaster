using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AudioPipeline.Shared.Models;

[Table("KnowledgeBase")]
public class KnowledgeRule
{
    [Key]
    public int Id { get; set; }

    public int BookId { get; set; }
    public int? ChunkId { get; set; }

    [Required, MaxLength(200)]
    public string Parameter { get; set; } = string.Empty;

    [Required, MaxLength(500)]
    public string Value { get; set; } = string.Empty;

    [MaxLength(50)]
    public string? Unit { get; set; }

    [MaxLength(100)]
    public string? Genre { get; set; }

    public string? Rationale { get; set; }

    [MaxLength(500)]
    public string? Source { get; set; }

    public int Priority { get; set; } = 1;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [ForeignKey(nameof(BookId))]
    public KnowledgeBook Book { get; set; } = null!;
}
