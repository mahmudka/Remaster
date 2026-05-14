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
        IBrowserFile? referenceFile,
        List<string> selectedBlocks)
    {
        var jobId      = Guid.NewGuid().ToString("N")[..12].ToUpper();
        var outputPath = Path.Combine(
            _config["OutputFolder"] ?? Path.Combine(Path.GetTempPath(), "AudioPipeline"),
            jobId);
        Directory.CreateDirectory(outputPath);

        var inputPath = Path.Combine(outputPath, audioFile.Name);
        await using var fs = File.Create(inputPath);
        await audioFile.OpenReadStream(maxAllowedSize: 500 * 1024 * 1024).CopyToAsync(fs);

        string? refPath = null;
        if (referenceFile is not null)
        {
            refPath = Path.Combine(outputPath, "ref_" + referenceFile.Name);
            await using var rfs = File.Create(refPath);
            await referenceFile.OpenReadStream(maxAllowedSize: 500 * 1024 * 1024).CopyToAsync(rfs);
        }

        var session = new MixSession
        {
            JobId      = jobId,
            InputFile  = inputPath,
            OutputPath = outputPath,
            Status     = "Pending",
            BlocksRun  = string.Join(",", selectedBlocks),
        };
        _db.MixSessions.Add(session);
        await _db.SaveChangesAsync();

        // Fire and forget — orchestrator runs in background
        _ = _orchestrator.RunPipelineAsync(jobId, inputPath, outputPath, refPath, selectedBlocks);

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
                await _http.PostAsync($"{GetMixUrl()}/learn", form);
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
            var resp = await _http.PostAsync($"{GetMixUrl()}/learn", form);
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

    // ── Voice Models (RVC) ───────────────────────────────────────────────────

    public async Task<List<VoiceModel>> GetVoiceModelsAsync()
        => await _db.VoiceModels.OrderByDescending(m => m.IsDefault).ThenBy(m => m.Name).ToListAsync();

    public async Task<VoiceModel?> GetDefaultVoiceModelAsync()
        => await _db.VoiceModels.FirstOrDefaultAsync(m => m.IsDefault);

    public async Task<VoiceModel> AddVoiceModelAsync(
        string name, string modelPath, string? indexPath, string? description)
    {
        var model = new VoiceModel
        {
            Name        = name,
            ModelPath   = modelPath,
            IndexPath   = indexPath,
            Description = description,
        };
        _db.VoiceModels.Add(model);
        await _db.SaveChangesAsync();
        return model;
    }

    public async Task DeleteVoiceModelAsync(int id)
    {
        var m = await _db.VoiceModels.FindAsync(id);
        if (m is not null) { _db.VoiceModels.Remove(m); await _db.SaveChangesAsync(); }
    }

    public async Task SetDefaultVoiceModelAsync(int id)
    {
        await _db.VoiceModels.ExecuteUpdateAsync(s => s.SetProperty(m => m.IsDefault, false));
        await _db.VoiceModels
            .Where(m => m.Id == id)
            .ExecuteUpdateAsync(s => s.SetProperty(m => m.IsDefault, true));
    }

    public async Task<(bool Online, bool LibOk)> CheckRvcServiceAsync()
    {
        try
        {
            var resp = await _http.GetAsync($"{GetRvcUrl()}/health");
            if (!resp.IsSuccessStatusCode) return (false, false);
            var doc = await resp.Content.ReadFromJsonAsync<System.Text.Json.JsonElement>();
            var libOk = doc.TryGetProperty("rvc", out var r) && r.GetBoolean();
            return (true, libOk);
        }
        catch { return (false, false); }
    }

    // ── Service URLs ──────────────────────────────────────────────────────────

    public string GetStemsUrl() => _config["Microservices:StemsUrl"] ?? "http://localhost:8001";
    public string GetMixUrl()   => _config["Microservices:MixUrl"]   ?? "http://localhost:8002";
    public string GetVstUrl()   => _config["Microservices:VstUrl"]   ?? "http://localhost:8003";
    public string GetRvcUrl()   => _config["Microservices:RvcUrl"]   ?? "http://localhost:8004";
}
