namespace AudioPipeline.Shared.DTOs;

public class SubmitFeedbackDto
{
    public int SessionId { get; set; }
    public int Rating { get; set; }
    public List<string> FeedbackTags { get; set; } = new();
    public string? UserNote { get; set; }
}

public class FeedbackDto
{
    public int Id { get; set; }
    public int SessionId { get; set; }
    public int Rating { get; set; }
    public List<string> FeedbackTags { get; set; } = new();
    public string? UserNote { get; set; }
    public DateTime CreatedAt { get; set; }
}
