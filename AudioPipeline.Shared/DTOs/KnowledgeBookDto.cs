namespace AudioPipeline.Shared.DTOs;

public class KnowledgeBookDto
{
    public int Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string? Author { get; set; }
    public string? Genre { get; set; }
    public int Priority { get; set; }
    public bool IsProcessed { get; set; }
    public int TotalChunks { get; set; }
}

public class AddBookDto
{
    public string Title { get; set; } = string.Empty;
    public string? Author { get; set; }
    public string FilePath { get; set; } = string.Empty;
    public string? Genre { get; set; }
    public int Priority { get; set; } = 1;
}
