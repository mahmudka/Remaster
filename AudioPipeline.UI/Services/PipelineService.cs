using AudioPipeline.Shared.Data;
using AudioPipeline.Shared.Models;
using Microsoft.AspNetCore.Components.Forms;
using Microsoft.EntityFrameworkCore;
using System.Net.Http.Json;
using System.Text.Json;

namespace AudioPipeline.UI.Services;

public class PipelineService
{
    private readonly HttpClient _http;
    private readonly AudioPipelineContext _db;
    private readonly IConfiguration _config;
    private readonly ILogger<PipelineService> _logger;
    private readonly OrchestratorService _orchestrator;

    public PipelineService(
        HttpClient http,
        AudioPipelineContext db,
        IConfiguration config,
        ILogger<PipelineService> logger,
        OrchestratorService orchestrator)
    {
        _http         = http;
        _db           = db;
        _config       = config;
        _logger       = logger;
        _orchestrator = orchestrator;
    }

    // ── Session management ────────────────────────────────────────────────────

    public async Task<string> StartAsync(
        IBrowserFile audioFile,
        float targetLufs = -14f)
    {
        var jobId      = Guid.NewGuid().ToString("N")[..12].ToUpper();
        var outputPath = Path.Combine(
            _config["OutputFolder"] ?? Path.Combine(Path.GetTempPath(), "AudioPipeline"),
            jobId);
        Directory.CreateDirectory(outputPath);

        var inputPath = Path.Combine(outputPath, audioFile.Name);
        await using var fs = File.Create(inputPath);
        await audioFile.OpenReadStream(maxAllowedSize: 500 * 1024 * 1024).CopyToAsync(fs);

        var session = new MixSession
        {
            JobId      = jobId,
            InputFile  = inputPath,
            OutputPath = outputPath,
            Status     = "Pending",
        };
        _db.MixSessions.Add(session);
        await _db.SaveChangesAsync();

        _ = _orchestrator.RunPipelineAsync(jobId, inputPath, outputPath, targetLufs);

        return jobId;
    }

    public async Task<MixSession?> GetSessionAsync(string jobId)
        => await _db.MixSessions
            .Include(s => s.Feedbacks)
            .FirstOrDefaultAsync(s => s.JobId == jobId);

    public async Task<List<MixSession>> GetRecentSessionsAsync(int count = 20)
        => await _db.MixSessions
            .Include(s => s.Feedbacks)
            .OrderByDescending(s => s.CreatedAt)
            .Take(count)
            .ToListAsync();

    // ── Feedback ──────────────────────────────────────────────────────────────

    public async Task SubmitFeedbackAsync(
        int sessionId, int rating,
        List<string> tags, string? note)
    {
        var feedback = new UserFeedback
        {
            SessionId        = sessionId,
            Rating           = rating,
            FeedbackTagsJson = JsonSerializer.Serialize(tags),
            UserNote         = note,
        };
        _db.UserFeedbacks.Add(feedback);
        await _db.SaveChangesAsync();

        // Trigger learning on the mix service
        var session = await _db.MixSessions.FindAsync(sessionId);
        if (session?.Genre is not null)
        {
            try
            {
                var form = new MultipartFormDataContent();
                form.Add(new StringContent(session.Genre), "genre");
                form.Add(new StringContent(sessionId.ToString()), "session_id");
                await _http.PostAsync($"{GetAudioUrl()}/learn", form);
            }
            catch (Exception ex)
            {
                _logger.LogWarning("Learning trigger failed: {Msg}", ex.Message);
            }
        }
    }

    // ── Skill profiles ────────────────────────────────────────────────────────

    public async Task<List<SkillProfile>> GetSkillProfilesAsync()
        => await _db.SkillProfiles
            .OrderByDescending(p => p.UpdatedAt)
            .ToListAsync();

    // ── Learning ──────────────────────────────────────────────────────────────

    public async Task<List<LearnedRule>> GetLearnedRulesAsync(string? genre = null)
    {
        var q = _db.LearnedRules.AsQueryable();
        if (!string.IsNullOrEmpty(genre))
            q = q.Where(r => r.Genre == genre);
        return await q.OrderBy(r => r.Genre).ThenByDescending(r => r.Confidence).ToListAsync();
    }

    public async Task<List<string>> GetGenresAsync()
        => await _db.MixSessions
            .Where(s => s.Genre != null && s.Genre != "")
            .Select(s => s.Genre!)
            .Distinct()
            .OrderBy(g => g)
            .ToListAsync();

    public async Task<int> TriggerLearningAsync(string genre)
    {
        try
        {
            var form = new MultipartFormDataContent();
            form.Add(new StringContent(genre), "genre");
            form.Add(new StringContent("0"), "session_id");
            var resp = await _http.PostAsync($"{GetAudioUrl()}/learn", form);
            if (resp.IsSuccessStatusCode)
            {
                var doc = await resp.Content.ReadFromJsonAsync<System.Text.Json.JsonElement>();
                return doc.TryGetProperty("rules_updated", out var v) ? v.GetInt32() : 0;
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning("Learning trigger failed: {Msg}", ex.Message);
        }
        return 0;
    }

    // ── Service URL ───────────────────────────────────────────────────────────

    public string GetAudioUrl() => _config["Microservices:AudioUrl"] ?? "http://localhost:8001";
}
