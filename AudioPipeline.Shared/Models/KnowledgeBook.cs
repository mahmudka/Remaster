using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AudioPipeline.Shared.Models;

[Table("KnowledgeBooks")]
public class KnowledgeBook
{
    [Key]
    public int Id { get; set; }

    [Required, MaxLength(500)]
    public string Title { get; set; } = string.Empty;

    [MaxLength(255)]
    public string? Author { get; set; }

    [MaxLength(1000)]
    public string? FilePath { get; set; }

    [MaxLength(100)]
    public string? Genre { get; set; }

    public int Priority { get; set; } = 1;
    public bool IsProcessed { get; set; } = false;
    public int TotalChunks { get; set; } = 0;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public ICollection<KnowledgeRule> Rules { get; set; } = new List<KnowledgeRule>();
}
