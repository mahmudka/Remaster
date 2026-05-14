using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AudioPipeline.Shared.Models;

[Table("BookChunks")]
public class BookChunk
{
    [Key]
    public int Id { get; set; }

    public int BookId { get; set; }
    public int ChunkIndex { get; set; }

    [Required]
    public string Content { get; set; } = string.Empty;

    public int? TokenCount { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [ForeignKey(nameof(BookId))]
    public KnowledgeBook Book { get; set; } = null!;
}
